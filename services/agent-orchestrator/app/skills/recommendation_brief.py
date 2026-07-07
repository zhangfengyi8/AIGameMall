"""
account-recommendation-brief skill 的 Python 实现。
职责：将已澄清的买家需求转化为搜索过滤条件、排序权重、推荐策略和降级方案。
"""


def build_query(intake_result: dict, candidate_count: int = 10) -> dict:
    """根据 intake 结果构建搜索查询和推荐策略。

    返回值符合 account-recommendation-brief SKILL.md 定义的 Output Contract。
    """
    slots = intake_result["slots"]
    firm = intake_result["firm_requirements"]
    soft = intake_result["soft_preferences"]
    goals = slots["account_goal"]
    budget = slots["budget"]
    heroes = slots["heroes"]
    skins = slots["skins"]
    rank = slots["rank"]
    risk_pref = slots["risk_preference"]

    filters = {}
    sc = slots["platform"].get("server_code")
    if sc:
        filters["server_code"] = sc
    if budget.get("max") is not None:
        price_max = budget["max"] * 100
        if budget.get("flexible"):
            price_max = int(price_max * 1.2)
        filters["price_max"] = price_max
    if budget.get("min") is not None:
        filters["price_min"] = budget["min"] * 100
    if heroes["must_have"]:
        filters["must_have_heroes"] = heroes["must_have"]
    if skins["must_have"]:
        filters["must_have_skins"] = skins["must_have"]
    if rank.get("current"):
        filters["min_rank"] = rank["current"]
    if risk_pref.get("requires_platform_guarantee"):
        filters["requires_platform_guarantee"] = True

    must_have = list(firm)
    nice_to_have = list(soft)

    weights = {
        "must_have_match": 100,
        "budget_fit": 30,
        "preferred_skin_coverage": 25,
        "skin_quality": 20,
        "hero_coverage": 15,
        "rank_or_power": 15,
        "asset_depth": 10,
        "risk_safety": 20,
    }

    if "skin_collection" in goals:
        weights["preferred_skin_coverage"] = 35
        weights["skin_quality"] = 30
        weights["budget_fit"] = 20
    if "rank_climb" in goals:
        weights["rank_or_power"] = 35
        weights["hero_coverage"] = 20
    if "value_for_money" in goals:
        weights["budget_fit"] = 40
        weights["preferred_skin_coverage"] = 15
    if risk_pref.get("retrieval_risk_tolerance") == "low":
        weights["risk_safety"] = 40

    tie_breakers = ["价格低优先", "交易保护完整度优先", "命名英雄/皮肤更多优先"]

    explain_fields = ["价格", "皮肤数量", "皮肤品质", "段位", "VIP等级", "实名状态", "风险等级"]

    risk_checks = []
    if risk_pref.get("retrieval_risk_tolerance") == "low":
        risk_checks.append("low_risk_filter")
    if risk_pref.get("real_name_requirement"):
        risk_checks.append("real_name_check")
    if not risk_checks:
        risk_checks = ["real_name_check", "retrieval_risk_check", "platform_guarantee_check"]

    fallbacks = []
    if heroes["must_have"]:
        fallbacks.append("relax_non_required_heroes")
    if skins["must_have"]:
        fallbacks.append("substitute_skin_same_hero_same_quality")
    if soft:
        fallbacks.append("drop_soft_preferences")
    if budget.get("flexible") and budget.get("max") is not None:
        fallbacks.append("expand_budget_20pct")
    if not fallbacks:
        fallbacks = ["relax_soft_preferences", "offer_similar_price_range"]

    never_relax = []
    if sc:
        never_relax.append("platform")
    if budget.get("max") is not None and not budget.get("flexible"):
        never_relax.append("budget_max")
    if heroes["must_have"]:
        never_relax.append("required_heroes")
    if skins["must_have"]:
        never_relax.append("required_skins")
    if risk_pref.get("retrieval_risk_tolerance") == "low":
        never_relax.append("risk_level")

    return {
        "query": {
            "filters": filters,
            "must_have": must_have,
            "nice_to_have": nice_to_have,
        },
        "ranking": {
            "weights": weights,
            "tie_breakers": tie_breakers,
        },
        "recommendation_policy": {
            "max_items": min(candidate_count, 10),
            "explain_fields": explain_fields,
            "risk_checks": risk_checks,
            "fallbacks": fallbacks,
            "never_relax": never_relax,
        },
        "buyer_message_guidance": [],
    }


def generate_explanation(
    account: dict,
    metrics: dict | None,
    brief: dict,
    rank: int,
) -> str:
    """生成单个账号的推荐说明。"""
    policy = brief.get("recommendation_policy", {})
    explain_fields = policy.get("explain_fields", [])

    parts = [f"{rank}. {account.get('listingId', '未知')}"]
    details = []

    if "价格" in explain_fields:
        price = account.get("salePrice", 0)
        details.append(f"价格 {price}元")
    if "皮肤数量" in explain_fields and metrics:
        sc = metrics.get("skinCount", 0)
        details.append(f"皮肤 {sc}个")
    if "段位" in explain_fields:
        rn = account.get("rankName", "?")
        rs = account.get("rankStars", 0)
        details.append(f"段位 {rn} {rs}星")
    if "VIP等级" in explain_fields:
        vl = account.get("vipLevel", "?")
        details.append(f"V{vl}")
    if "实名状态" in explain_fields:
        real = "✅ 支持二次实名" if account.get("secondaryRealNameStatus") == "SUPPORTED" else "⚠️ 不支持二次实名"
        details.append(real)
    if "风险等级" in explain_fields:
        risk_items = account.get("risk", {}).get("items", [])
        if any(i.get("level") == "high" for i in risk_items):
            details.append("⚠️ 高风险")
        elif any(i.get("level") == "medium" for i in risk_items):
            details.append("⚠️ 中风险")
        else:
            details.append("✅ 低风险")

    parts.append(" | ".join(details))
    return "\n".join(parts)