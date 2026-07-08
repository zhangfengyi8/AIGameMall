"""
规则降级引擎：当模型不可用时，用技能模块（intake + brief）生成推荐。
"""
import re

from app.skills.conversation_intent import classify_conversation_intent
from app.skills.requirement_intake import intake as rule_intake, search_params_from_intake
from app.skills.recommendation_brief import build_query
from app.tools.search import _do_search

MAX_RECOMMENDATION_CARDS = 3
CANDIDATE_POOL_LIMIT = 60
NO_MORE_ACCOUNTS_REPLY = "暂时没有其他符合要求的账号了呢~ 可以适当放宽预算、区服或皮肤要求，我再帮你找找。"
_SHOWN_IDS_MARKER = "[[__shown_account_ids__]]"


def _extract_shown_ids(history: list[dict] | None) -> set[str]:
    shown: set[str] = set()
    for item in history or []:
        if not isinstance(item, dict):
            continue
        content = item.get("content", "")
        if isinstance(content, str) and content.startswith(_SHOWN_IDS_MARKER):
            for token in content[len(_SHOWN_IDS_MARKER):].strip().split(","):
                token = token.strip()
                if token:
                    shown.add(token)
    return shown


def _strip_markers(history: list[dict] | None) -> list[dict]:
    cleaned = []
    for item in history or []:
        if isinstance(item, dict):
            content = item.get("content", "")
            if isinstance(content, str) and content.startswith(_SHOWN_IDS_MARKER):
                continue
        cleaned.append(item)
    return cleaned


def _with_shown_marker(history_list: list[dict], shown_ids: set[str]) -> list[dict]:
    cleaned = _strip_markers(history_list)
    if shown_ids:
        cleaned = cleaned + [
            {"role": "system", "content": _SHOWN_IDS_MARKER + " " + ",".join(sorted(shown_ids))}
        ]
    return cleaned


def run_fallback(user_message: str, history: list[dict] | None = None) -> dict:
    """规则降级入口：使用 buyer-requirement-intake + account-recommendation-brief 技能。"""
    intent_result = classify_conversation_intent(user_message, history)
    if not intent_result["should_search"]:
        return _controlled_chat_result(user_message, history, intent_result)

    is_next_batch = bool(intent_result.get("next_batch"))
    shown_ids = _extract_shown_ids(history)
    base_history = _strip_markers(history)

    # Step 1: 需求理解
    merged_message = _merged_user_message(user_message, history)
    next_history = [*base_history, {"role": "user", "content": user_message}]
    intake_result = rule_intake(merged_message)

    if not intake_result["ready_for_recommendation"]:
        # 需求不明确，直接追问
        clarifying = intake_result.get("clarifying_question", "")
        if not clarifying:
            clarifying = "预算大概多少？最高能接受到多少？另外你要 QQ 还是微信，安卓还是 iOS？"
        reply = f"好的，我先了解下你的需求。{clarifying}"
        return {
            "reply": reply,
            "recommendations": [],
            "intake": intake_result,
            "history": _with_shown_marker([*next_history, {"role": "assistant", "content": reply}], shown_ids),
        }

    # Step 2: 构建推荐策略
    brief = build_query(intake_result)
    fallbacks = brief["recommendation_policy"]["fallbacks"]

    # Step 3: 执行搜索（放大候选池）
    search_params = search_params_from_intake(intake_result)
    search_params.setdefault("limit", CANDIDATE_POOL_LIMIT)
    accounts = _do_search(**search_params)

    # Step 4: 如果结果太少，尝试降级
    if len(accounts) < 3 and fallbacks:
        relaxed_params = dict(search_params)
        relaxed_params.pop("rank_name", None)
        if "expand_budget_20pct" in fallbacks:
            b_max = relaxed_params.get("budget_max")
            if b_max:
                relaxed_params["budget_max"] = int(b_max * 1.2)
        accounts2 = _do_search(**relaxed_params)
        if len(accounts2) > len(accounts):
            accounts = accounts2

    # Step 5: “换一批”排除已展示账号；普通推荐重置已展示集合
    if is_next_batch:
        candidates = [a for a in accounts if a.get("listingId") not in shown_ids]
    else:
        candidates = accounts
    selected_accounts = candidates[:MAX_RECOMMENDATION_CARDS]

    if is_next_batch and not selected_accounts:
        return {
            "reply": NO_MORE_ACCOUNTS_REPLY,
            "recommendations": [],
            "intake": intake_result,
            "history": _with_shown_marker(
                [*next_history, {"role": "assistant", "content": NO_MORE_ACCOUNTS_REPLY}], shown_ids
            ),
        }

    selected_ids = {a.get("listingId") for a in selected_accounts if a.get("listingId")}
    new_shown = (shown_ids | selected_ids) if is_next_batch else set(selected_ids)

    # Step 6: 生成回复
    reply = generate_fallback_reply(selected_accounts, user_message)
    return {
        "reply": reply,
        "recommendations": _format_fallback_recommendations(selected_accounts),
        "intake": intake_result,
        "history": _with_shown_marker(
            [*next_history, {"role": "assistant", "content": reply}], new_shown
        ),
    }


def _controlled_chat_result(user_message: str, history: list[dict] | None, intent_result: dict) -> dict:
    reply = intent_result.get("reply", "")
    shown_ids = _extract_shown_ids(history)
    base_history = _strip_markers(history)
    return {
        "reply": reply,
        "recommendations": [],
        "intake": {
            "intent": intent_result.get("intent", "unknown"),
            "ready_for_recommendation": False,
            "controlled_chat": True,
        },
        "history": _with_shown_marker(
            [
                *base_history,
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": reply},
            ],
            shown_ids,
        ),
    }


def _merged_user_message(user_message: str, history: list[dict] | None = None) -> str:
    user_parts: list[str] = [user_message.strip()]
    for item in history or []:
        if not isinstance(item, dict) or item.get("role") != "user":
            continue
        content = item.get("content", "")
        if isinstance(content, str) and content.strip():
            user_parts.append(content.strip())
    return "\n".join(user_parts)


def _format_fallback_recommendations(accounts: list[dict]) -> list[dict]:
    metrics_by_lid = {m["listingId"]: m for m in _do_load("accountMetrics.json")}
    skin_master = {s["skinId"]: s for s in _do_load("skinMaster.json")}
    skin_ids_by_lid: dict[str, list[str]] = {}
    for row in _do_load("accountSkin.json"):
        skin_ids_by_lid.setdefault(row["listingId"], []).append(row["skinId"])

    recommendations = []
    for account in accounts:
        listing_id = account.get("listingId", "")
        metrics = metrics_by_lid.get(listing_id, {})
        skin_names = [
            skin_master.get(skin_id, {}).get("skinName", "")
            for skin_id in skin_ids_by_lid.get(listing_id, [])
        ]
        recommendations.append(
            {
                "account_id": listing_id,
                "server_code": account.get("serverCode"),
                "price": account.get("salePrice", 0),
                "vip_level": account.get("vipLevel"),
                "rank_name": account.get("rankName"),
                "rank_stars": account.get("rankStars"),
                "anti_addiction": account.get("antiAddictionStatus"),
                "secondary_real_name": account.get("secondaryRealNameStatus"),
                "change_bind": account.get("changeBindStatus"),
                "skin_count": metrics.get("skinCount", 0),
                "hero_count": metrics.get("heroCount", 0),
                "value_score": metrics.get("valueScore", 0),
                "skins": [name for name in skin_names if name][:3],
            }
        )
    return recommendations


def _do_load(filename: str) -> list[dict]:
    from app.tools.search import _lj

    return _lj(filename)


def generate_fallback_reply(accounts: list[dict], user_text: str) -> str:
    """根据搜索结果生成面向买家的自然推荐文案，不暴露内部 ID 或策略说明。"""
    selected_recommendations = _format_fallback_recommendations(accounts[:3])
    if not selected_recommendations:
        return "暂时找不到相关账号，换个条件试试吧。比如放宽预算、平台或皮肤要求，我可以继续帮你筛。"

    if len(selected_recommendations) == 1:
        lines = ["找到一个比较匹配的账号，可以优先看看。"]
    else:
        lines = ["我筛到几款比较接近你需求的账号，可以按优先级看看："]

    labels = ["推荐一", "推荐二", "推荐三"]
    for index, recommendation in enumerate(selected_recommendations):
        lines.append(_format_recommendation_paragraph(labels[index], recommendation))
    lines.append(_shared_risk_note(selected_recommendations))
    return "\n".join(lines)


def _format_recommendation_paragraph(label: str, recommendation: dict) -> str:
    price = recommendation.get("price", 0)
    rank_name = recommendation.get("rank_name") or "未知段位"
    vip_level = recommendation.get("vip_level") or 0
    server_name = _server_label(recommendation.get("server_code"))
    skins = recommendation.get("skins") or []
    core_asset = _core_asset_text(skins)
    value_text = _value_text(recommendation)
    return (
        f"{label}：这款是{server_name}，价格{price}元，{rank_name}段位，V{vip_level}。"
        f"核心亮点是{core_asset}，{value_text}。"
    )


def _core_asset_text(skins: list[str]) -> str:
    if not skins:
        return "账号基础资产比较均衡"
    if "杀手不太冷" in skins:
        other_skins = [skin for skin in skins if skin != "杀手不太冷"]
        if other_skins:
            return f"带孙尚香荣耀典藏「杀手不太冷」，同时还有{'、'.join(other_skins)}等高价值皮肤"
        return "带孙尚香荣耀典藏「杀手不太冷」"
    return f"拥有{'、'.join(skins)}等核心皮肤"


def _risk_summary(recommendation: dict) -> str:
    real = "支持二次实名" if recommendation.get("secondary_real_name") == "SUPPORTED" else "不支持二次实名"
    bind = "可换绑" if recommendation.get("change_bind") == "FULL_SUPPORTED" else "不可换绑"
    anti = "无防沉迷" if recommendation.get("anti_addiction") == "NONE" else "有防沉迷限制"
    return f"{real}、{bind}，{anti}"


def _value_text(recommendation: dict) -> str:
    score = recommendation.get("value_score", 0) or 0
    price = recommendation.get("price", 0) or 0
    if score >= 85:
        return "预算内性价比更突出"
    if price >= 4000:
        return "配置更偏收藏型，但价格明显更高"
    return "整体配置比较均衡"


def _shared_risk_note(recommendations: list[dict]) -> str:
    if not recommendations:
        return ""
    if all(item.get("secondary_real_name") == "SUPPORTED" for item in recommendations):
        real = "支持二次实名"
    else:
        real = "部分账号实名条件需要重点确认"
    if all(item.get("change_bind") == "FULL_SUPPORTED" for item in recommendations):
        bind = "支持换绑"
    else:
        bind = "部分账号换绑条件需要重点确认"
    if all(item.get("anti_addiction") == "NONE" for item in recommendations):
        anti = "无防沉迷"
    else:
        anti = "部分账号可能存在防沉迷限制"
    if len(recommendations) == 1:
        return f"下单前注意事项：这款账号显示{real}、{bind}，且{anti}；建议再确认实名可改和换绑流程。"
    return f"交易安全上，这几款都显示{real}、{bind}，且{anti}；下单前建议再确认实名可改和换绑流程。"


def _server_label(server_code: str | None) -> str:
    labels = {
        "ANDROID_QQ": "安卓QQ区",
        "ANDROID_WECHAT": "安卓微信区",
        "IOS_QQ": "苹果QQ区",
        "IOS_WECHAT": "苹果微信区",
    }
    return labels.get(server_code or "", "未知区服")
