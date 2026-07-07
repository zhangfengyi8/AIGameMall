# JSON 数据结构设计

## 设计目标

当前阶段不使用数据库，账号商品、标签和样例数据都存放在 `data` 目录下的 JSON 文件中。

第一版只支持王者荣耀账号，样例账号准备 20 条；字段结构仍保留 `game` 对象，方便后续扩展多游戏。

JSON 结构需要同时满足：

- 商城列表展示。
- 商品详情展示。
- 条件筛选。
- AI 导购推荐。
- 性价比分析。
- 风险提示。

## 文件规划

建议使用以下文件：

- `data/accounts/accounts.json`: 账号商品主数据。
- `data/tags/games.json`: 游戏枚举与游戏配置。
- `data/tags/ranks.json`: 段位枚举与排序权重。
- `data/tags/assets.json`: 皮肤、英雄、稀有资产等标签。
- `data/samples/user_queries.json`: 用户导购需求样例。

## 账号商品结构

`accounts.json` 建议为数组，每个元素表示一个账号商品。

```json
[
  {
    "id": "acc_100001",
    "title": "王者荣耀 V8 皮肤号 全英雄 多限定",
    "game": {
      "id": "honor_of_kings",
      "name": "王者荣耀"
    },
    "category": "皮肤号",
    "status": "on_sale",
    "price": 899,
    "original_price": 1099,
    "valuation": {
      "fair_price": 980,
      "value_level": "good",
      "value_label": "性价比高",
      "valuation_note": "核心皮肤数量较多，报价低于系统估价。"
    },
    "account_assets": {
      "hero_count": 120,
      "is_full_heroes": true,
      "skin_count": 268,
      "legend_skin_count": 35,
      "limited_skin_count": 42,
      "collector_skin_count": 3,
      "vip_level": 8,
      "account_level": 30
    },
    "rank": {
      "current": "荣耀王者",
      "peak_score": 1800,
      "season": "S36"
    },
    "highlights": {
      "heroes": ["李白", "孙尚香", "露娜"],
      "skins": ["凤求凰", "末日机甲", "紫霞仙子"],
      "tags": ["全英雄", "多限定", "荣耀典藏", "低风险"]
    },
    "trade": {
      "bind_status": "可换绑",
      "real_name_status": "可二次实名",
      "platform": "QQ",
      "region": "安卓 QQ 区",
      "seller_guarantee": true
    },
    "risk": {
      "level": "low",
      "label": "低",
      "score": 18,
      "items": ["支持换绑", "卖家已验号", "平台担保交易"],
      "warnings": []
    },
    "display": {
      "cover_url": "",
      "badges": ["热卖", "高性价比"],
      "sort_weight": 100
    },
    "created_at": "2026-07-06T00:00:00+08:00",
    "updated_at": "2026-07-06T00:00:00+08:00"
  }
]
```

## 字段说明

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | string | 账号唯一 ID |
| `title` | string | 商品标题 |
| `game` | object | 游戏信息 |
| `category` | string | 商品分类，例如皮肤号、技术号、低价号 |
| `status` | string | 商品状态，第一版主要使用 `on_sale` |
| `price` | number | 卖家报价 |
| `original_price` | number | 原价或划线价，可为空 |
| `valuation` | object | 系统估价与性价比结论 |
| `account_assets` | object | 英雄、皮肤、等级、贵族等资产信息 |
| `rank` | object | 段位与巅峰赛信息 |
| `highlights` | object | 推荐展示用亮点信息 |
| `trade` | object | 换绑、实名、区服、担保等交易信息 |
| `risk` | object | 风险等级、风险项和提示 |
| `display` | object | 前端展示辅助字段 |

## 风险等级

| level | label | 说明 |
| --- | --- | --- |
| `low` | 低 | 支持换绑、信息完整、平台担保 |
| `medium` | 中 | 有部分限制或信息不完整 |
| `high` | 高 | 不支持换绑、实名风险或找回风险较高 |

## 性价比等级

| value_level | value_label | 说明 |
| --- | --- | --- |
| `excellent` | 捡漏 | 明显低于系统估价 |
| `good` | 性价比高 | 价格低于或接近系统估价 |
| `fair` | 价格合理 | 价格与资产基本匹配 |
| `expensive` | 偏贵 | 价格明显高于系统估价 |

## 查询设计要求

账号 JSON 应支持以下查询：

- 按游戏查询。
- 按价格区间查询。
- 按关键词查询。
- 按分类查询。
- 按段位查询。
- 按英雄查询。
- 按皮肤查询。
- 按标签查询。
- 按风险等级查询。
- 按性价比等级查询。

## 后续可扩展字段

后续如进入真实交易阶段，可扩展：

- 卖家信息。
- 验号报告。
- 历史成交价。
- 收藏数。
- 浏览数。
- 库存状态。
- 商品上下架原因。


