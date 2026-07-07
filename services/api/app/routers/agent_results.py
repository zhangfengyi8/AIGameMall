from app.schemas.agent_results import (
    AgentRecommendation,
    AgentResultRenderRequest,
    AgentResultRenderResponse,
    FrontendAccountCard,
)


SERVER_LABELS = {
    "ANDROID_QQ": "安卓QQ",
    "ANDROID_WECHAT": "安卓微信",
    "IOS_QQ": "苹果QQ",
    "IOS_WECHAT": "苹果微信",
}


def render_agent_result(
    request: AgentResultRenderRequest,
) -> AgentResultRenderResponse:
    cards = [_to_frontend_card(recommendation) for recommendation in request.recommendations]
    return AgentResultRenderResponse(
        session_id=request.session_id,
        type="recommendations" if cards else "clarification",
        message=request.reply or request.agent_message or "",
        cards=cards,
        history=request.history,
        intake=request.intake,
    )


def _to_frontend_card(recommendation: AgentRecommendation) -> FrontendAccountCard:
    rank = _rank_text(recommendation)
    return FrontendAccountCard(
        id=recommendation.account_id,
        title=f"{rank} · V{recommendation.vip_level or 0} · {recommendation.skin_count}皮肤",
        price=recommendation.price,
        match=_match_score(recommendation.value_score),
        heroes=recommendation.hero_count,
        skins=recommendation.skin_count,
        rank=rank,
        vip=recommendation.vip_level,
        region=SERVER_LABELS.get(
            recommendation.server_code or "",
            recommendation.server_code or "未知区服",
        ),
        estValue=recommendation.price,
        estLabel="高性价比" if recommendation.value_score >= 80 else "可考虑",
        risk=_risk_label(recommendation),
        riskItems=[
            f"防沉迷：{recommendation.anti_addiction or '未知'}",
            f"实名：{recommendation.secondary_real_name or '未知'}",
            f"换绑：{recommendation.change_bind or '未知'}",
        ],
        highlightSkins=recommendation.skins[:3],
        detail_api=f"/api/v1/accounts/{recommendation.account_id}",
    )


def _rank_text(recommendation: AgentRecommendation) -> str:
    rank_name = recommendation.rank_name or "未知段位"
    if recommendation.rank_stars:
        return f"{rank_name}{recommendation.rank_stars}星"
    return rank_name


def _match_score(value_score: float) -> int:
    return max(0, min(100, round(value_score)))


def _risk_label(recommendation: AgentRecommendation) -> str:
    risk_fields = " ".join(
        [
            recommendation.secondary_real_name or "",
            recommendation.change_bind or "",
        ]
    )
    if "UNSUPPORTED" in risk_fields or "不可" in risk_fields:
        return "中"
    return "低"
