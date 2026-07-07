---
name: account-recommendation-brief
description: Use when the 王者荣耀 account shopping agent has a clarified buyer requirement or intake output and needs to produce account search filters, must-have and nice-to-have criteria, ranking weights, recommendation explanation guidance, risk checks, and fallback strategies without inventing inventory.
---

# Account Recommendation Brief

Use this skill after requirement intake and before presenting account recommendations. Convert a clarified buyer requirement into a compact recommendation plan that the account search layer and response generator can follow.

## Inputs

Use any of these inputs when available:

- The JSON output from `buyer-requirement-intake`.
- The latest buyer message plus prior clarified slots.
- Candidate account records returned by a search tool.
- Inventory schema or field mapping, if the runtime provides one.

If no candidate accounts are provided, generate search and ranking guidance only. Do not fabricate accounts, prices, screenshots, account IDs, or guarantees.

## Workflow

1. Read the buyer's firm requirements and soft preferences.
2. Convert firm requirements into `query.filters` or `query.must_have`.
3. Convert soft preferences into `query.nice_to_have` and ranking weights.
4. Add risk checks that match the buyer's risk tolerance.
5. Define concise recommendation explanation guidance for the response generator.
6. If exact matches may be scarce, provide fallback relaxations in a safe order.

## Output Contract

Return a JSON object with this shape:

```json
{
  "query": {
    "filters": {},
    "must_have": [],
    "nice_to_have": []
  },
  "ranking": {
    "weights": {},
    "tie_breakers": []
  },
  "recommendation_policy": {
    "max_items": 3,
    "explain_fields": [],
    "risk_checks": [],
    "fallbacks": []
  },
  "buyer_message_guidance": []
}
```

Keep keys stable even when values are empty. Use plain semantic field names when the inventory schema is not available.

## Query Rules

Map requirements this way:

- Platform or operating system the buyer explicitly states is a hard filter.
- Budget maximum is a hard filter unless `budget.flexible = true`.
- Required skins and heroes are `must_have`.
- Required rank, peak score, noble level, or asset count is a hard filter only when the user says "必须", "只要", "至少", or equivalent.
- "最好", "尽量", "多点", "性价比高", and "毕业一点" are soft preferences.
- Low-risk or platform-guaranteed transaction preference should filter or rank by risk fields when those fields exist.

Example semantic filters:

```json
{
  "platform.login_channel": "QQ",
  "platform.os": "安卓",
  "price.max": 1000,
  "risk.requires_platform_guarantee": true
}
```

## Ranking Guidance

Use weights that reflect the buyer's stated priorities. If the buyer does not give priorities, use this default order:

1. Firm requirement match.
2. Required skin or hero coverage.
3. Budget fit and value for money.
4. Rare or high-quality skin coverage.
5. Rank, peak score, combat power, and other progression assets.
6. Risk and transaction protection.

Suggested default weights:

```json
{
  "must_have_match": 100,
  "budget_fit": 30,
  "preferred_skin_coverage": 25,
  "skin_quality": 20,
  "hero_coverage": 15,
  "rank_or_power": 15,
  "asset_depth": 10,
  "risk_safety": 20
}
```

Adjust these weights when the user is clear:

- Skin collector: raise `preferred_skin_coverage` and `skin_quality`.
- Rank climber: raise `rank_or_power` and relevant hero coverage.
- Value buyer: raise `budget_fit` and require explicit tradeoff explanations.
- Low-risk buyer: raise `risk_safety` and filter out high-risk accounts when fields exist.

Tie-breakers:

- Prefer lower price when accounts satisfy the same must-have requirements.
- Prefer accounts with clearer transaction protection.
- Prefer accounts with more of the buyer's named heroes or skins.
- Prefer fewer irrelevant assets over a higher price when the buyer asked for value.

## Recommendation Explanation

For each recommended account, explain 2 to 4 points in this order:

1. Why it matches the buyer's main goal.
2. Which must-have or preferred skins, heroes, rank, or assets it covers.
3. How the price compares with the buyer's budget.
4. Any concrete risk or tradeoff.

Use direct, non-hype language. Do not say "绝对安全", "永久不找回", or "全网最低" unless the platform has verified data for that exact claim.

If a candidate lacks a desired item, state the tradeoff:

- "缺少凤求凰，但在 500 内皮肤总量更高。"
- "段位不高，但有你要的传说皮肤，适合收藏。"
- "价格略接近预算上限，优势是平台担保和低风险字段更完整。"

## Fallback Strategy

When no exact match exists, relax constraints in this order:

1. Relax soft preferences first, such as extra skin count, non-required heroes, or preferred rank.
2. Expand budget only if the buyer said the budget can float.
3. Replace a named non-required skin with same hero, same quality, or similar scarcity.
4. Offer accounts that match platform and budget but miss the least important preference.
5. Ask a follow-up question when every useful fallback would violate a firm requirement.

Do not relax:

- Platform or operating system if explicitly required.
- Required skin or hero if the user said it is mandatory.
- Maximum budget when the buyer said it cannot exceed that amount.
- Low-risk requirement when the user explicitly rejects high-risk accounts.

## Risk Checks

Include risk checks that the search layer or response generator should verify:

- Real-name status and whether transfer or secondary verification is supported.
- Historical retrieval or dispute risk indicators.
- Platform guarantee, escrow, or after-sale protection.
- Seller credibility or account listing completeness when available.
- Mismatch between advertised assets and structured inventory fields.

Risk message guidance:

- Say the system can prioritize lower-risk listings.
- Do not promise there is no retrieval risk.
- Explain what should be checked before payment.

## Examples

Input summary: `安卓 QQ，1000 内，皮肤多点，最好有几个传说`

Output emphasis:

- Hard filters: `platform.login_channel = QQ`, `platform.os = 安卓`, `price.max = 1000`.
- Nice-to-have: high skin count, several legendary skins.
- Ranking: raise `preferred_skin_coverage`, `skin_quality`, and `budget_fit`.
- Explanation: compare skin count, legendary coverage, price, and transaction protection.

Input summary: `500 内必须有李白凤求凰`

Output emphasis:

- Hard filters: `price.max = 500`, must-have skin `凤求凰`, must-have hero `李白` if skin ownership implies hero availability in inventory.
- Missing platform: request platform clarification if the search layer cannot search cross-platform.
- Fallback: do not substitute a different Li Bai skin unless the buyer agrees.
