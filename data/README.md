# data 数据目录说明

当前账号推荐与账号详情使用 `data/tags` 下的关联表数据，不再使用旧的
`data/accounts/accounts.json` 展示型账号文件。

## 账号关联表

| 文件 | 说明 | 主键/关联键 |
|---|---|---|
| `tags/accountListing.json` | 账号商品主表，包含价格、区服、段位、VIP、换绑与实名状态 | `listingId` |
| `tags/accountMetrics.json` | 账号检索指标，包含皮肤数、英雄数、资产估值、性价比评分 | `listingId` |
| `tags/accountHero.json` | 账号拥有英雄关系表 | `listingId`, `heroId` |
| `tags/accountSkin.json` | 账号拥有皮肤关系表 | `listingId`, `skinId` |
| `tags/heroMaster.json` | 英雄主数据 | `heroId` |
| `tags/skinMaster.json` | 皮肤主数据 | `skinId` |
| `tags/games.json` | 游戏枚举 | `gameCode` |
| `tags/ranks.json` | 段位枚举 | 段位编码/名称 |
| `tags/assets.json` | 资产标签配置 | 标签编码 |

Agent 搜索路径：

```text
services/agent-orchestrator/app/tools/search.py
  -> data/tags/accountListing.json
  -> data/tags/accountMetrics.json
  -> data/tags/accountHero.json
  -> data/tags/accountSkin.json
  -> data/tags/heroMaster.json
  -> data/tags/skinMaster.json
```

API 账号详情路径：

```text
services/api/app/data/accounts.py
  -> data/tags/accountListing.json
  -> data/tags/accountMetrics.json
  -> data/tags/accountHero.json
  -> data/tags/accountSkin.json
  -> data/tags/heroMaster.json
  -> data/tags/skinMaster.json
```

## skins.json 字段含义说明

> 数据来源：[ricochet.cn/wzry/skin](https://ricochet.cn/wzry/skin)

---

## 顶层字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `data` | array | 皮肤数据数组 |
| `status` | int | API 响应状态码，`1` 表示成功 |

## data[] 皮肤对象字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `big_picture_index` | int | 皮肤大图的展示索引/排序序号 |
| `big_picture_url` | string | 皮肤大图的 CDN 地址（腾讯云 COS） |
| `class_names` | string | 皮肤分类标签，多个标签用 `#` 分隔。常见标签：勇者品质、史诗品质、限定、源梦皮肤、珍品限定、珍品传说等 |
| `hero_title` | string | 所属英雄名称 |
| `low_price` | string | 皮肤最低价格（点券） |
| `nga_tid` | int | NGA 论坛关联帖子 ID，`-1` 表示无关联 |
| `official_url` | string | 官方皮肤详情页链接，空字符串表示无 |
| `online_time` | int | 皮肤上线时间的 Unix 时间戳（秒），`0` 表示未上线/待定 |
| `price` | string | 皮肤当前价格（点券） |
| `quality` | string | 皮肤品质等级（见下方对照表） |
| `score` | float | 皮肤评分（NGA 玩家评分） |
| `skin_id` | int | 皮肤唯一 ID |
| `skin_title` | string | 皮肤名称 |
| `vote_count` | int | 评分投票人数 |

## 品质等级对照表

| 品质 | 含义 |
|---|---|
| SS | 典藏 |
| SSR | 珍品 |
| S | 传说 |
| A | 史诗 |
| B | 勇者 |
| C | 伴生 |
| D | 原皮 |
