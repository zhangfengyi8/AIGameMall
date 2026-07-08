# 前后端对接说明

> 最后更新：2026-07-07

## 前端入口

前端入口文件：`frontend/index.html`

当前页面已经包含静态商城页面、账号卡片、详情弹窗、AI 悬浮球和 AI 对话窗口。

## Agent 返回体结构

AI 导购接口返回以下结构：

```json
{
  "reply": "自然语言推荐语",
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
  "history": [/* OpenAI Messages 格式 */],
  "intake": { /* 需求理解结果 */ }
}
```

## 前端字段映射

前端 AI 推荐区域渲染所需字段与后端字段对应关系：

| 前端渲染位置 | 使用字段 | 后端对应 |
|---|---|---|
| 卡片点击事件 | `a.id` | `account_id` |
| 卡片标题 | `a.title` | 后端不返回，前端按 rank+vip+skin_count 拼接 |
| 匹配度 | `a.match` | `value_score` 归一化到 0-100 |
| 英雄数 | `a.heroes` | `hero_count` |
| 皮肤数 | `a.skins` | `skin_count` |
| 段位 | `a.rank` | `rank_name` + `rank_stars` |
| VIP | `a.vip` | `vip_level` |
| 区服 | `a.region` | `server_code` 转译 |
| 价格 | `a.price` | `price` |
| 估价 | `a.estValue` | 当前无此字段，可用 `price` 占位 |
| 性价比 | `a.estLabel` | 当前无此字段，可用 value_score 推算 |
| 风险 | `a.risk` | 当前无统一字段，需要补充或前端忽略 |
| 风险详情 | `a.riskItems` | 当前无此字段 |

## 建议对接步骤

### 第一步：AI 对话框接入

当前前端 AI 对话框使用模拟数据（`frontend/index.html` 中第 1740 行附近 `handleAIMessage` 函数）。

改造点：

```javascript
// 当前模拟：
function handleAIMessage(msg) {
    const results = mockAccounts.filter(...);
    // 拼接 AI 回复和卡片
}

// 改为调用后端：
async function handleAIMessage(msg) {
    const resp = await fetch("/api/guide/chat", {
        method: "POST",
        body: JSON.stringify({ session_id, message: msg, history })
    });
    const data = await resp.json();
    // data.reply → 渲染 AI 文本
    // data.recommendations → 渲染推荐卡片列表
}
```

### 第二步：卡片渲染适配

前端 AI 推荐卡片模板在 `frontend/index.html` 第 1785-1807 行：

```javascript
// 当前模板使用模拟数据字段名：
html += `<div class="ai-card" onclick="openDetail(${a.id})">
    <span class="ai-card-title">${a.title}</span>
    <span class="ai-card-match">匹配 ${a.match}%</span>
    <span>${a.heroes}英雄</span>
    <span>${a.skins}皮肤</span>
    <span>${a.rank}</span>
    <span>V${a.vip}</span>
    <span>${a.region}</span>
    <span class="ai-card-price">¥${a.price}</span>
    <span>估价 ¥${a.estValue}</span>
    <span class="ai-card-value-tag">${a.estLabel}</span>
    <div class="ai-card-risk">风险${a.risk} · ${a.riskItems}</div>
</div>`;

// 改为使用后端字段：
html += `<div class="ai-card" onclick="openDetail('${card.account_id}')">
    <span class="ai-card-title">${card.rank_name || ''}${card.vip_level ? ' V'+card.vip_level : ''} · ${card.skin_count}皮肤</span>
    <span class="ai-card-match">${Math.round(card.value_score)}%</span>
    <span>${card.hero_count}英雄</span>
    <span>${card.skin_count}皮肤</span>
    <span>${card.rank_name} ${card.rank_stars}星</span>
    <span>V${card.vip_level}</span>
    <span>${serverCodeLabel(card.server_code)}</span>
    <span class="ai-card-price">¥${card.price}</span>
    <span class="ai-card-risk">防沉迷=${card.anti_addiction} · 实名=${card.secondary_real_name} · 换绑=${card.change_bind}</span>
</div>`;
```

### 第三步：server_code 转译函数

```javascript
function serverCodeLabel(code) {
    const map = {
        "ANDROID_QQ": "安卓QQ",
        "ANDROID_WECHAT": "安卓微信",
        "IOS_QQ": "苹果QQ",
        "IOS_WECHAT": "苹果微信"
    };
    return map[code] || code || "未知";
}
```

## 关键交互场景

### 场景一：用户需求明确

```
用户: "安卓QQ，500以内，皮肤多点"
  ↓ 后端返回
reply: "推荐以下3个账号..."
recommendations: [1-1-3张卡片]
history: [...]
  ↓ 前端渲染
AI 消息气泡: reply 文本
下方: 3 张可点击卡片
```

### 场景二：用户需求模糊

```
用户: "推荐个性价比高的号"
  ↓ 后端返回
reply: "预算大概多少？最高能接受到多少？"
recommendations: []  (空)
history: [...]
  ↓ 前端渲染
AI 消息气泡: reply 文本
无卡片展示
```

### 场景三：用户继续补充

```
用户: "500以内，安卓QQ"
  ↓ 后端收到 history + 新消息
  ↓ 后端返回
reply: "推荐以下3个账号..."
recommendations: [1-1-3张卡片]
  ↓ 前端渲染
AI 消息气泡 + 卡片
```

## 卡片点击行为

点击卡片触发 `openDetail(account_id)`，当前已有一个详情弹窗函数。当前弹窗使用模拟数据，后续可改造为调用 `GET /api/accounts/{account_id}` 获取详情。

## 待改造点

- [ ] 将 AI 对话框的模拟数据替换为 `/api/guide/chat` 真实调用。
- [ ] 适配后端 format_card 字段名。
- [ ] 添加 `serverCodeLabel()` 转译函数。
- [ ] 需求模糊的场景下不出卡片。
- [ ] 增加 loading 状态。
- [ ] 增加接口失败时的错误提示。
- [ ] 多轮对话时传 history 字段。