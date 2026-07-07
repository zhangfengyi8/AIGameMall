"""
规则降级引擎：当模型不可用时，用技能模块（intake + brief）生成推荐。
"""
import re

from app.skills.requirement_intake import intake as rule_intake, search_params_from_intake
from app.skills.recommendation_brief import build_query
from app.tools.search import _do_search


def run_fallback(user_message: str) -> dict:
    """规则降级入口：使用 buyer-requirement-intake + account-recommendation-brief 技能。"""
    # Step 1: 需求理解
    intake_result = rule_intake(user_message)

    if not intake_result["ready_for_recommendation"]:
        # 需求不明确，直接追问
        clarifying = intake_result.get("clarifying_question", "")
        if not clarifying:
            clarifying = "预算大概多少？最高能接受到多少？另外你要 QQ 还是微信，安卓还是 iOS？"
        reply = f"好的，我先了解下你的需求。{clarifying}"
        return {
            "reply": reply,
            "history": [
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": reply},
            ],
        }

    # Step 2: 构建推荐策略
    brief = build_query(intake_result)
    filters = brief["query"]["filters"]
    weights = brief["ranking"]["weights"]
    fallbacks = brief["recommendation_policy"]["fallbacks"]

    # Step 3: 执行搜索
    search_params = search_params_from_intake(intake_result)
    accounts = _do_search(**search_params)

    # Step 4: 如果结果太少，尝试降级
    if len(accounts) < 3 and fallbacks:
        # 先去掉软偏好，放宽搜索
        relaxed_params = dict(search_params)
        relaxed_params.pop("heroes", None)
        relaxed_params.pop("skins", None)
        relaxed_params.pop("rank_name", None)
        if "expand_budget_20pct" in fallbacks:
            b_max = relaxed_params.get("budget_max")
            if b_max:
                relaxed_params["budget_max"] = int(b_max * 1.2)
        accounts2 = _do_search(**relaxed_params)
        if len(accounts2) > len(accounts):
            accounts = accounts2

    # Step 5: 生成回复
    reply = generate_fallback_reply(accounts, user_message)
    return {
        "reply": reply,
        "history": [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": reply},
        ],
    }


def generate_fallback_reply(accounts: list[dict], user_text: str) -> str:
    """根据搜索结果生成模板推荐回复。"""
    if not accounts:
        return "抱歉，暂时没有找到完全符合你要求的账号。你可以试试放宽预算或者调整一下条件。"

    lines = [f"为你推荐以下 {len(accounts[:3])} 个账号：\n"]
    for i, lst in enumerate(accounts[:3], 1):
        lid = lst.get("listingId", "?")
        sc = lst.get("serverCode", "?")
        sp = lst.get("salePrice", 0)
        rn = lst.get("rankName", "?")
        rs = lst.get("rankStars", 0)
        vip = lst.get("vipLevel", "?")
        anti = "有防沉迷" if lst.get("antiAddictionStatus") == "RESTRICTED" else "无防沉迷"
        real = "支持二次实名" if lst.get("secondaryRealNameStatus") == "SUPPORTED" else "不支持二次实名"
        bind = "可换绑" if lst.get("changeBindStatus") == "FULL_SUPPORTED" else "不可换绑"

        lines.append(
            f"{i}. {lid} [{sc}]"
            f"\n   价格：{sp}元  段位：{rn} {rs}星"
            f"\n   VIP{vip}  {anti}  {real}  {bind}"
        )
        lines.append("")

    return "\n".join(lines)