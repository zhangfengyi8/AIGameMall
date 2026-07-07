# skins.json 字段含义说明

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
