---
name: buyer-requirement-intake
description: Use when the game account shopping agent needs to understand a user buying, finding, comparing, or consulting about 王者荣耀 accounts; extract budget, platform, account goals, rank, heroes, skins, assets, risk preference, and deal preference, then ask concise clarifying questions when the request is too vague for recommendation.
---

# Buyer Requirement Intake

Use this skill before account search or recommendation. Convert the buyer's message and recent dialogue context into a structured requirement summary. Ask only the minimum clarification needed to move the buyer toward useful account recommendations.

## Workflow

1. Detect whether the user is buying, finding, comparing, or asking advice about a 王者荣耀 account.
2. Extract explicit conditions from the user's message. Preserve uncertainty instead of guessing.
3. Infer safe defaults only when they are low risk:
   - Set `game` to `王者荣耀` when the conversation is already about this product.
   - Treat "预算 500", "500 内", and "不超过 500" as `budget.max = 500`.
   - Treat "左右", "可加点", and "能浮动" as `budget.flexible = true`.
4. Classify each condition as a firm requirement, soft preference, or unknown.
5. Decide whether the request is ready for recommendation.
6. If not ready, ask 1 to 2 high-impact clarifying questions. Do not ask a long questionnaire.

## Output Contract

Return a JSON object with this shape:

```json
{
  "intent": "buy_account",
  "confidence": 0.0,
  "slots": {
    "game": "王者荣耀",
    "platform": {
      "login_channel": null,
      "os": null,
      "raw_text": null
    },
    "budget": {
      "min": null,
      "max": null,
      "currency": "CNY",
      "flexible": false,
      "raw_text": null
    },
    "account_goal": [],
    "rank": {
      "current": null,
      "peak": null,
      "peak_score": null,
      "raw_text": null
    },
    "heroes": {
      "must_have": [],
      "preferred": [],
      "lanes": []
    },
    "skins": {
      "must_have": [],
      "preferred": [],
      "quality": [],
      "tags": [],
      "count_preference": null
    },
    "assets": {
      "noble_level": null,
      "inscriptions": null,
      "hero_count": null,
      "skin_count": null,
      "glory_crystal": null,
      "other": []
    },
    "risk_preference": {
      "real_name_requirement": null,
      "retrieval_risk_tolerance": null,
      "requires_platform_guarantee": null,
      "raw_text": null
    },
    "deal_preference": {
      "price_first": false,
      "asset_first": false,
      "same_platform_first": false,
      "acceptable_missing_items": []
    }
  },
  "firm_requirements": [],
  "soft_preferences": [],
  "missing_required_slots": [],
  "missing_optional_slots": [],
  "clarifying_question": "",
  "ready_for_recommendation": false,
  "notes": []
}
```

Use `null` for unknown scalar values and empty arrays for unknown list values. Keep `confidence` between `0` and `1`.

## Slot Guidance

- `platform.login_channel`: use `QQ_Android`, `QQ_IOS`, `WX_Andriod`, `WX_IOS`
- `account_goal`: use concise labels such as `skin_collection`, `rank_climb`, `combat_power`, `hero_pool`, `noble_level`, `value_for_money`, `gift`.
- `skins.quality`: normalize to `典藏`, `无双`, `珍品`, `传说`, `史诗`, `勇者`, or `限定` when the user names a quality or scarcity class.
- `risk_preference.retrieval_risk_tolerance`: use `low`, `medium`, `high`, or `unknown`.
- `firm_requirements`: include conditions the user presents as non-negotiable, such as "必须有凤求凰" or "只要安卓 QQ".
- `soft_preferences`: include conditions expressed as "最好", "尽量", "多点", or "性价比高".

## Readiness Rules

Set `ready_for_recommendation = true` when:

- The intent is account buying, finding, or comparison.
- The request has either a budget or a clear account goal.
- Any missing platform field can be safely handled by the inventory search layer, or the answer can explicitly present cross-platform results.

Set `ready_for_recommendation = false` when:

- The user only says vague phrases such as "推荐个号", "性价比高的", or "毕业号" with no budget and no goal.
- The user's stated need depends on platform compatibility and platform is unknown.
- The request is mainly about risk guarantees, refunds, or account safety rather than selecting an account.

## Clarifying Questions

Ask at most 2 questions in one turn. Prefer a single question when one answer would unlock search.

Priority order:

1. Budget: "预算大概多少，最高能接受到多少？"
2. Platform: "你要 QQ 还是微信，安卓还是 iOS？"
3. Goal: "更看重皮肤收藏、排位段位、战力，还是整体性价比？"
4. Must-have assets: "有没有必须要有的英雄或皮肤？"
5. Risk: "是否只看平台担保、低找回风险的账号？"

Examples:

- User: "帮我找个性价比高的号"
  - Ask: "预算大概多少？另外你要 QQ/微信、安卓/iOS 哪种？"
- User: "500 内有李白凤求凰吗"
  - Ask: "你要 QQ 还是微信，安卓还是 iOS？"
- User: "安卓 QQ，1000 内，皮肤多点"
  - Ready: true. Treat platform and budget as firm, skin count as soft preference.

## Safety Rules

- Do not promise an account will never be retrieved. Say that the system can prioritize lower-risk accounts and platform-guaranteed transactions.
- Do not help bypass real-name verification, minors protection, platform controls, or payment safeguards.
- If the user asks for "包不找回", convert it to a low-risk requirement and include a risk note.
- Do not invent inventory, prices, or account details.
