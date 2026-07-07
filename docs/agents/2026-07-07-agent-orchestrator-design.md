# Agent 编排服务技术设计

> 本文档基于 Brainstorming 讨论结论编写，随开发进度同步更新。
> 最后更新：2026-07-07

## 技术栈

| 项 | 选择 | 理由 |
|---|---|---|
| Agent 框架 | OpenAI Agents SDK | 原生 Tool calling，自动管理 tool call 循环 |
| 模型 | GPT-4o-mini | 成本可控，满足第一版需求 |
| 数据源 | 本地 JSON 文件（关联表） | 当前阶段不引入数据库 |

## 架构概览

当前版本采用 **规则引擎前置 + 单 Agent + 单 Tool** 架构，集成两个 SKILL.md 定义的技能模块。

### 核心流程

```
用户输入
    │
    ▼
① buyer-requirement-intake（规则引擎：app/skills/requirement_intake.py）
    ├─ 提取预算、平台、段位、英雄/皮肤、风险偏好
    ├─ 区分必须条件 vs 软偏好
    └─ 判断 ready_for_recommendation
    │
    ├── 需求模糊 ──→ LLM 追问 ──→ 返回 { reply }（无卡片）
    │
    ▼
② account-recommendation-brief（规则引擎：app/skills/recommendation_brief.py）
    ├─ 将需求转为搜索过滤条件
    ├─ 根据用户目标调整排序权重
    └─ 制定降级策略和不可放松条件
    │
    ▼
③ 规则搜索（app/tools/search.py）
    ├─ 从 JSON 关联表中筛选候选账号
    └─ 按价值评分排序，最多返回 10 个
    │
    ▼
④ 候选数据注入 LLM
    ├─ 注入内容：需求摘要 + 推荐策略 + 候选账号列表
    ├─ LLM 负责挑选推荐、写推荐语
    └─ 不依赖 LLM 输出结构化数据
    │
    ▼
⑤ 返回
    └─ { reply: "推荐语", recommendations: [卡片], history, intake }
```

### 关键设计原则

1. **搜索只做一次**：后端规则引擎搜完账号后，卡片数据和注入 LLM 的候选数据同源。
2. **大模型只输出文本**：负责写推荐语和解释，不输出结构化 JSON。
3. **卡片数据独立保证**：前端展示的 recommendation 卡片直接来自后端规则搜索结果，不依赖 LLM 输出。
4. **需求模糊时不出卡片**：LLM 先追问，后端返回 `recommendations: []`。

## 技能模块

### buyer-requirement-intake（app/skills/requirement_intake.py）

职责：将用户自然语言需求转化为结构化槽位。

````python
def intake(text: str) -> dict:
    """
    返回值（符合 SKILL.md Output Contract）：
    {
        "intent": "buy_account",
        "confidence": 0.0-1.0,
        "slots": {
            "game": "王者荣耀",
            "platform": { "login_channel", "os", "server_code" },
            "budget": { "min", "max", "currency", "flexible", "raw_text" },
            "account_goal": ["skin_collection", "rank_climb", ...],
            "rank": { "current", "peak", "peak_score" },
            "heroes": { "must_have", "preferred", "lanes" },
            "skins": { "must_have", "preferred", "quality", "tags", "count_preference" },
            "risk_preference": { "retrieval_risk_tolerance", "requires_platform_guarantee" },
            "deal_preference": { "price_first", "asset_first", ... }
        },
        "firm_requirements": [...],
        "soft_preferences": [...],
        "missing_required_slots": ["budget"],
        "clarifying_question": "预算大概多少？",
        "ready_for_recommendation": bool,
    }
    """
````

追问优先级：
1. 预算 → 2. 平台 → 3. 目标英雄/皮肤 → 4. 风险偏好

## account-recommendation-brief（app/skills/recommendation_brief.py）

职责：将澄清后的需求转为搜索策略和排序指引。

````python
def build_query(intake_result: dict, candidate_count: int = 10) -> dict:
    """
    返回值：
    {
        "query": { "filters": {...}, "must_have": [], "nice_to_have": [] },
        "ranking": {
            "weights": {
                "must_have_match": 100,
                "budget_fit": 30,
                "preferred_skin_coverage": 25,
                "skin_quality": 20,
                "hero_coverage": 15,
                "rank_or_power": 15,
                "asset_depth": 10,
                "risk_safety": 20,
            },
            "tie_breakers": [...]
        },
        "recommendation_policy": {
            "max_items": 10,
            "explain_fields": [...],
            "risk_checks": [...],
            "fallbacks": ["drop_soft_preferences", "expand_budget_20pct", ...],
            "never_relax": ["platform", "budget_max", "required_heroes", ...]
        },
    }
    """
````

### 排序权重调整规则

| 用户目标 | 调整 |
|---|---|
| skin_collection | preferred_skin_coverage +10, skin_quality +10, budget_fit -10 |
| rank_climb | rank_or_power +20, hero_coverage +5 |
| value_for_money | budget_fit +20, preferred_skin_coverage -10 |
| 低风险偏好 | risk_safety +20 |

### 降级策略（按顺序）

1. 放开软偏好（额外皮肤数、非必须英雄等）
2. 同一英雄同品质替换皮肤
3. 预算可浮动时扩大 20%
4. 推荐近似价位替代

**不放松**：平台、预算上限（不可浮动时）、必须英雄/皮肤、低风险要求

## Tool 设计

### 唯一 Tool：search_accounts

```python
@function_tool
def search_accounts(
    game_code: str | None = "WZ",
    server_code: str | None = None,
    budget_min: int | None = None,
    budget_max: int | None = None,
    heroes: list[str] | None = None,
    skins: list[str] | None = None,
    keyword: str | None = None,
    rank_name: str | None = None,
    anti_addiction: str | None = None,
    secondary_real_name: str | None = None,
    change_bind: str | None = None,
    limit: int = 10,
) -> list[dict]:
```

- 数据来源 `data/tags/` 目录下的 JSON 关联表
- 预算单位为分（元 * 100），如 `budget_max=50000` 表示 500 元
- server_code: `ANDROID_QQ`, `ANDROID_WECHAT`, `IOS_QQ`, `IOS_WECHAT`
- 内部实现 `_do_search()` 同时被 fallback 模式复用

### 关联表结构

JSON 多表关联查询：

| 文件 | 用途 | 关联键 |
|---|---|---|
| accountListing.json | 账号主表 | listingId |
| accountMetrics.json | 资产评分 | listingId |
| accountHero.json | 账号-英雄映射 | listingId, heroId |
| accountSkin.json | 账号-皮肤映射 | listingId, skinId |
| heroMaster.json | 英雄名称字典 | heroId |
| skinMaster.json | 皮肤名称字典 | skinId |

## 降级策略（无模型时）

`app/fallback/rule_engine.py` 复用两套技能模块：

```
用户输入 → intake() → build_query() → _do_search() → 模板回复
```

## 目录结构

```
services/agent-orchestrator/
├── app/
│   ├── agent.py                    # Agent 定义 + 规则前置流程
│   ├── instructions.py             # System Prompt（含双 skill 指导）
│   ├── skills/
│   │   ├── requirement_intake.py   # buyer-requirement-intake 实现
│   │   └── recommendation_brief.py # account-recommendation-brief 实现
│   ├── tools/search.py             # search_accounts Tool
│   ├── schemas/
│   │   ├── detail.py               # 卡片格式化（含关联表查询）
│   │   └── recommendation.py       # RecommendResult 模型
│   └── fallback/rule_engine.py     # 规则降级
├── test_agent.py                   # 交互式测试
├── requirements.txt
├── .env / .env.example
└── skills/                         # SKILL.md 源文件
    ├── buyer-requirement-intake/
    └── account-recommendation-brief/
```

## 推荐卡片结构

后端 `format_card()` 返回的完整字段：

```json
{
  "account_id": "listing_10001",
  "accountId": "acc_100001",
  "game_code": "WZ",
  "server_code": "ANDROID_QQ",
  "price": 4200,
  "vip_level": 8,
  "rank_name": "荣耀王者",
  "rank_stars": 82,
  "anti_addiction": "NONE",
  "secondary_real_name": "SUPPORTED",
  "change_bind": "FULL_SUPPORTED",
  "skin_count": 5,
  "hero_count": 5,
  "value_score": 8.04,
  "heroes": ["英雄名称列表"],
  "skins": ["皮肤名称列表"]
}
```

## Agent 返回体

```json
{
  "reply": "自然语言推荐语",
  "recommendations": [/* format_card 数组 */],
  "history": [/* OpenAI Messages 格式 */],
  "intake": { /* intake() 原始输出 */ }
}
```

## 多轮对话

- SDK 内置 History 机制
- 服务端内存维护 session_id → message_history
- 30 分钟无操作自动清理
- 第一版不做持久化

## 第一版状态

- [x] 单 Agent + 双 Skill 模块
- [x] 规则引擎前置需求理解
- [x] 搜索只做一次，卡片数据独立保证
- [x] 需求模糊时 LLM 追问
- [x] 引导用户提供预算和平台
- [x] 规则降级兜底
- [ ] 流式输出
- [ ] 语音输入
- [ ] 持久化存储
- [ ] 多 Agent handoff