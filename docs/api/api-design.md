# API 接口设计草案

> 最后更新：2026-07-07

## 设计目标

API 服务位于 `services/api`，负责给 `frontend` 提供商城列表、账号详情和 AI 导购对话接口。

当前阶段 API 读取本地 JSON 数据，不使用数据库。

## 统一响应格式

所有接口建议使用统一响应结构：

```json
{
  "success": true,
  "code": "OK",
  "message": "success",
  "data": {},
  "request_id": "req_20260706120000001"
}
```

错误响应：

```json
{
  "success": false,
  "code": "ACCOUNT_NOT_FOUND",
  "message": "账号不存在",
  "data": null,
  "request_id": "req_20260706120000001"
}
```

## 接口列表

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/health` | 健康检查 |
| GET | `/api/accounts` | 账号列表查询 |
| GET | `/api/accounts/{account_id}` | 账号详情查询 |
| POST | `/api/guide/chat` | AI 导购对话 |
| POST | `/api/guide/chat/stream` | AI 导购流式对话 |
| GET | `/api/tags` | 标签与筛选配置 |

## POST `/api/guide/chat`

AI 导购对话接口，直接调用 `services/agent-orchestrator` 的 Agent 模块。

### 请求体

```json
{
  "session_id": "sess_001",
  "message": "安卓QQ，500以内，皮肤多点",
  "history": [
    {"role": "user", "content": "帮我找账号"},
    {"role": "assistant", "content": "预算大概多少？最高能接受到多少？"}
  ]
}
```

### Agent 内部处理流程

```
请求到达
  │
  ├─ 规则引擎 intake() 理解需求
  │   ├─ 需求模糊 → LLM 追问 → 返回 { reply, recommendations: [] }
  │   └─ 需求明确 →
  │       ├─ 规则引擎 search_params_from_intake() 生成搜索参数
  │       ├─ 规则引擎 _do_search() 搜索候选账号
  │       ├─ 规则引擎 build_query() 构建推荐策略
  │       ├─ 候选数据 + 策略注入 LLM
  │       ├─ LLM 生成推荐语
  │       └─ 返回 { reply, recommendations, history, intake }
```

### 响应 data 示例

```json
{
  "session_id": "sess_001",
  "reply": "帮你筛选了安卓QQ区500元以内的账号，推荐以下3个...",
  "recommendations": [
    {
      "account_id": "listing_10019",
      "accountId": "acc_100019",
      "game_code": "WZ",
      "server_code": "ANDROID_QQ",
      "price": 399,
      "vip_level": 4,
      "rank_name": "钻石",
      "rank_stars": 0,
      "anti_addiction": "NONE",
      "secondary_real_name": "SUPPORTED",
      "change_bind": "FULL_SUPPORTED",
      "skin_count": 5,
      "hero_count": 5,
      "value_score": 101.55,
      "heroes": ["英雄A", "英雄B"],
      "skins": ["皮肤X", "皮肤Y"]
    }
  ],
  "history": [
    {"role": "user", "content": "安卓QQ，500以内，皮肤多点"},
    {"role": "assistant", "content": "帮你筛选了..."}
  ],
  "intake": {
    "intent": "buy_account",
    "confidence": 0.8,
    "firm_requirements": ["预算不超过500元", "登录渠道：QQ", "系统：安卓"],
    "soft_preferences": ["皮肤数量多"],
    "ready_for_recommendation": true,
    "clarifying_question": ""
  }
}
```

### 关键说明

- **卡片与推荐语同源**：recommendations 来自后端规则搜索，LLM 只写文本推荐语
- **需求模糊时**：recommendations 为空数组，reply 为追问内容
- **history 保持 SDK 格式**：可原样传给下一次请求
- **intake 为调试/透明度字段**：前端可忽略，后端日志使用

## 流式接口（待实现）

### POST `/api/guide/chat/stream`

SSE 事件流：

| event | 说明 |
|---|---|
| `message_delta` | LLM 回复文本片段 |
| `recommendation` | 完整推荐卡片 JSON |
| `intake` | 需求理解结果 |
| `done` | 响应结束 |
| `error` | 错误信息 |

## GET `/api/health`

### 响应示例

```json
{
  "success": true,
  "code": "OK",
  "message": "success",
  "data": {
    "status": "ok",
    "service": "api",
    "agent_available": true
  },
  "request_id": "req_xxx"
}
```

## GET `/api/accounts`

### Query 参数

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `game_code` | string | 否 | 游戏编码，默认 WZ |
| `server_code` | string | 否 | 区服 |
| `keyword` | string | 否 | 搜索关键词 |
| `min_price` | number | 否 | 最低价（元） |
| `max_price` | number | 否 | 最高价（元） |
| `rank_name` | string | 否 | 段位 |
| `page` | number | 否 | 页码，默认 1 |
| `page_size` | number | 否 | 每页数量，默认 20 |

### 响应 data 示例

```json
{
  "items": [
    {
      "account_id": "listing_10001",
      "game_code": "WZ",
      "server_code": "ANDROID_QQ",
      "price": 4200,
      "vip_level": 8,
      "rank_name": "荣耀王者",
      "rank_stars": 82,
      "skin_count": 5,
      "hero_count": 5,
      "value_score": 8.04
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 1
  }
}
```

## GET `/api/accounts/{account_id}`

返回完整账号详情+d量信息，字段同 format_card() + 关联查询的英雄/皮肤列表，参考 data/tags/ 下的关联表结构。

## GET `/api/tags`

### 响应 data 示例

```json
{
  "games": [{"id": "WZ", "name": "王者荣耀"}],
  "server_codes": [
    {"code": "ANDROID_QQ", "label": "安卓QQ"},
    {"code": "ANDROID_WECHAT", "label": "安卓微信"},
    {"code": "IOS_QQ", "label": "苹果QQ"},
    {"code": "IOS_WECHAT", "label": "苹果微信"}
  ],
  "ranks": ["青铜", "白银", "黄金", "铂金", "钻石", "星耀", "王者", "无双王者", "荣耀王者"]
}
```

## 待确认事项

- [x] API 服务直接调用 Agent 编排模块，不拆独立 HTTP 服务。
- [ ] 流式接口是否需要支持。
- [ ] 前端是直接调用 agent-orchestrator 模块，还是通过 api 服务转发。