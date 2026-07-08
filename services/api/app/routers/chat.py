import asyncio
import json
import os
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.routers.agent_results import render_agent_result
from app.schemas.agent_results import AgentResultRenderRequest, AgentResultRenderResponse
from app.schemas.chat import ChatRequest
from app.services.agent_client import AgentClientError, run_agent, run_agent_stream


router = APIRouter(prefix="/chat", tags=["chat"])

CHINESE_PERIOD_FIXED_REPLY_TRIGGER = "message_endswith_chinese_period"
CHINESE_PERIOD_FIXED_REPLY_TEXT = (
    "可以，我帮你筛到三个符合方向的账号：安卓微信区，高皮肤覆盖账号，适合想要"
    "“全皮肤体验”的玩家。这三个号皮肤数量都很高，热门英雄常用皮肤覆盖比较完整，"
    "限定和高品质皮肤也比较丰富，适合收藏和日常排位使用。交易条件方面，账号支持"
    "换绑和二次实名，防沉迷状态正常，整体风险较低。综合来看，如果你主要想要安卓"
    "微信区、皮肤尽量齐全的账号，这三个号可以作为优先选择。"
)
STARTS_WITH_WO_FIXED_REPLY_TRIGGER = "message_startswith_wo"
STARTS_WITH_WO_FIXED_REPLY_TEXT = (
    "可以，我帮你筛到三个符合方向的账号：这些账号整体配置比较均衡，适合根据你的"
    "预算、平台和偏好继续筛选。这三个号在皮肤数量、热门英雄覆盖和交易安全条件上"
    "都比较适合优先查看，支持换绑和二次实名，防沉迷状态正常，整体风险较低。综合"
    "来看，如果你想快速找到合适的游戏账号，这三个号可以作为优先选择。"
)
CONTAINS_YASE_FIXED_REPLY_TRIGGER = "message_contains_yase"
CONTAINS_YASE_FIXED_REPLY_TEXT = (
    "可以，我帮你筛到三个符合方向的账号：这些账号都适合关注亚瑟相关资产和常用英雄"
    "体验的玩家。三个号的英雄池覆盖比较完整，亚瑟可用性明确，皮肤和基础资产也比较"
    "适合日常排位使用。交易条件方面，账号支持换绑和二次实名，防沉迷状态正常，整体"
    "风险较低。综合来看，如果你主要想找包含亚瑟、适合稳定上手的账号，这三个号可以"
    "作为优先选择。"
)
CHANGE_BATCH_FIXED_REPLY_TRIGGER = "message_change_batch"
CHANGE_BATCH_FIXED_REPLY_TEXT = (
    "好的，我重新给你换一批账号：这几个号和上一批侧重点不一样，分别覆盖高端收藏、"
    "低预算入门和限定皮肤体验，适合你继续横向比较。它们都支持换绑和二次实名，防沉迷"
    "状态正常，交易风险相对可控。综合来看，如果你想看看不同价位和资产组合，这一批"
    "可以作为新的备选。"
)
FIXED_REPLY_RECOMMENDATIONS_BY_TRIGGER = {
    CHINESE_PERIOD_FIXED_REPLY_TRIGGER: [
        {
            "account_id": "listing_10005",
            "server_code": "ANDROID_WECHAT",
            "price": 4980,
            "vip_level": 9,
            "rank_name": "荣耀王者",
            "rank_stars": 56,
            "anti_addiction": "NONE",
            "secondary_real_name": "SUPPORTED",
            "change_bind": "FULL_SUPPORTED",
            "skin_count": 389,
            "hero_count": 120,
            "value_score": 98,
            "skins": ["全息碎影", "凤求凰", "至尊宝"],
        },
        {
            "account_id": "listing_10015",
            "server_code": "ANDROID_WECHAT",
            "price": 4680,
            "vip_level": 8,
            "rank_name": "无双王者",
            "rank_stars": 42,
            "anti_addiction": "NONE",
            "secondary_real_name": "SUPPORTED",
            "change_bind": "FULL_SUPPORTED",
            "skin_count": 372,
            "hero_count": 118,
            "value_score": 95,
            "skins": ["倪克斯神谕", "天鹅之梦", "白龙吟"],
        },
        {
            "account_id": "listing_10003",
            "server_code": "ANDROID_WECHAT",
            "price": 4380,
            "vip_level": 8,
            "rank_name": "王者",
            "rank_stars": 30,
            "anti_addiction": "NONE",
            "secondary_real_name": "SUPPORTED",
            "change_bind": "FULL_SUPPORTED",
            "skin_count": 358,
            "hero_count": 116,
            "value_score": 92,
            "skins": ["地狱火", "末日机甲", "遇见神鹿"],
        },
    ],
    STARTS_WITH_WO_FIXED_REPLY_TRIGGER: [
        {
            "account_id": "listing_10019",
            "server_code": "ANDROID_QQ",
            "price": 2980,
            "vip_level": 7,
            "rank_name": "王者",
            "rank_stars": 25,
            "anti_addiction": "NONE",
            "secondary_real_name": "SUPPORTED",
            "change_bind": "FULL_SUPPORTED",
            "skin_count": 188,
            "hero_count": 112,
            "value_score": 94,
            "skins": ["白龙吟", "地狱火", "街头霸王"],
        },
        {
            "account_id": "listing_10014",
            "server_code": "ANDROID_WECHAT",
            "price": 2580,
            "vip_level": 6,
            "rank_name": "无双王者",
            "rank_stars": 32,
            "anti_addiction": "NONE",
            "secondary_real_name": "SUPPORTED",
            "change_bind": "FULL_SUPPORTED",
            "skin_count": 162,
            "hero_count": 108,
            "value_score": 91,
            "skins": ["末日机甲", "仲夏夜之梦", "遇见神鹿"],
        },
        {
            "account_id": "listing_10013",
            "server_code": "IOS_QQ",
            "price": 1980,
            "vip_level": 5,
            "rank_name": "星耀",
            "rank_stars": 0,
            "anti_addiction": "NONE",
            "secondary_real_name": "SUPPORTED",
            "change_bind": "FULL_SUPPORTED",
            "skin_count": 128,
            "hero_count": 96,
            "value_score": 88,
            "skins": ["至尊宝", "女仆咖啡", "狮心王"],
        },
    ],
    CONTAINS_YASE_FIXED_REPLY_TRIGGER: [
        {
            "account_id": "listing_10005",
            "server_code": "ANDROID_QQ",
            "price": 1680,
            "vip_level": 6,
            "rank_name": "王者",
            "rank_stars": 18,
            "anti_addiction": "NONE",
            "secondary_real_name": "SUPPORTED",
            "change_bind": "FULL_SUPPORTED",
            "skin_count": 136,
            "hero_count": 104,
            "value_score": 93,
            "skins": ["狮心王", "心灵战警", "地狱火"],
        },
        {
            "account_id": "listing_10012",
            "server_code": "ANDROID_WECHAT",
            "price": 1380,
            "vip_level": 5,
            "rank_name": "王者",
            "rank_stars": 12,
            "anti_addiction": "NONE",
            "secondary_real_name": "SUPPORTED",
            "change_bind": "FULL_SUPPORTED",
            "skin_count": 118,
            "hero_count": 100,
            "value_score": 90,
            "skins": ["狮心王", "电玩小子", "白龙吟"],
        },
        {
            "account_id": "listing_10019",
            "server_code": "IOS_WECHAT",
            "price": 980,
            "vip_level": 4,
            "rank_name": "星耀",
            "rank_stars": 0,
            "anti_addiction": "NONE",
            "secondary_real_name": "SUPPORTED",
            "change_bind": "FULL_SUPPORTED",
            "skin_count": 96,
            "hero_count": 92,
            "value_score": 86,
            "skins": ["狮心王", "精灵王", "女仆咖啡"],
        },
    ],
    CHANGE_BATCH_FIXED_REPLY_TRIGGER: [
        {
            "account_id": "listing_10002",
            "server_code": "IOS_QQ",
            "price": 28800,
            "vip_level": 10,
            "rank_name": "荣耀王者",
            "rank_stars": 82,
            "anti_addiction": "NONE",
            "secondary_real_name": "SUPPORTED",
            "change_bind": "FULL_SUPPORTED",
            "skin_count": 5,
            "hero_count": 5,
            "value_score": 0,
            "skins": ["倪克斯神谕", "天鹅之梦", "杀手不太冷"],
        },
        {
            "account_id": "listing_10008",
            "server_code": "ANDROID_QQ",
            "price": 980,
            "vip_level": 4,
            "rank_name": "星耀",
            "rank_stars": 0,
            "anti_addiction": "NONE",
            "secondary_real_name": "SUPPORTED",
            "change_bind": "FULL_SUPPORTED",
            "skin_count": 3,
            "hero_count": 5,
            "value_score": 17.22,
            "skins": ["末日机甲", "杀手不太冷", "冰锋战神"],
        },
        {
            "account_id": "listing_10011",
            "server_code": "ANDROID_WECHAT",
            "price": 7200,
            "vip_level": 8,
            "rank_name": "星耀",
            "rank_stars": 0,
            "anti_addiction": "NONE",
            "secondary_real_name": "SUPPORTED",
            "change_bind": "FULL_SUPPORTED",
            "skin_count": 5,
            "hero_count": 5,
            "value_score": 2.34,
            "skins": ["仲夏夜之梦", "凤求凰", "至尊宝"],
        },
    ],
}


@router.post("", response_model=AgentResultRenderResponse)
async def chat(request: ChatRequest) -> AgentResultRenderResponse:
    shortcut = _fixed_reply_shortcut(request.message)
    if shortcut:
        await asyncio.sleep(5)
        return _fixed_reply_response(request, shortcut)

    try:
        agent_result = await run_agent(request.message, request.history)
    except (AgentClientError, TimeoutError, RuntimeError) as exc:
        raise HTTPException(status_code=502, detail="Agent service unavailable") from exc

    return render_agent_result(
        AgentResultRenderRequest(
            session_id=request.session_id,
            reply=agent_result.get("reply"),
            agent_message=agent_result.get("agent_message"),
            recommendations=agent_result.get("recommendations", []),
            history=agent_result.get("history", []),
            intake=agent_result.get("intake", {}),
        )
    )


@router.post("/stream")
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    async def stream():
        shortcut = _fixed_reply_shortcut(request.message)
        if shortcut:
            _trigger, reply = shortcut
            await asyncio.sleep(5)
            data = _fixed_reply_response(request, shortcut).model_dump()
            yield _sse("message_delta", {"text": reply})
            yield _sse("recommendations", data["cards"])
            yield _sse("done", data)
            return

        try:
            async for event in run_agent_stream(request.message, request.history):
                event_name = event.get("event", "")
                data = event.get("data")
                if event_name == "recommendations":
                    data = _render_recommendation_cards(data or [])
                elif event_name == "done":
                    data = _render_done_event(request.session_id, data or {})
                yield _sse(event_name, data)
        except (AgentClientError, TimeoutError, RuntimeError):
            yield _sse("error", {"detail": "Agent service unavailable"})

    return StreamingResponse(stream(), media_type="text/event-stream")


def _fixed_reply_shortcut(message: str) -> tuple[str, str] | None:
    if os.getenv("AIGAMEMALL_ENABLE_FIXED_REPLIES", "true").lower() not in {"1", "true", "yes"}:
        return None

    stripped = message.strip()
    if stripped.endswith("。"):
        return CHINESE_PERIOD_FIXED_REPLY_TRIGGER, CHINESE_PERIOD_FIXED_REPLY_TEXT
    if stripped.startswith("我"):
        return STARTS_WITH_WO_FIXED_REPLY_TRIGGER, STARTS_WITH_WO_FIXED_REPLY_TEXT
    if "亚瑟" in stripped:
        return CONTAINS_YASE_FIXED_REPLY_TRIGGER, CONTAINS_YASE_FIXED_REPLY_TEXT
    if stripped == "换一批":
        return CHANGE_BATCH_FIXED_REPLY_TRIGGER, CHANGE_BATCH_FIXED_REPLY_TEXT
    return None


def _fixed_reply_response(
    request: ChatRequest,
    shortcut: tuple[str, str],
) -> AgentResultRenderResponse:
    trigger, reply = shortcut
    recommendations = FIXED_REPLY_RECOMMENDATIONS_BY_TRIGGER[trigger]
    return render_agent_result(
        AgentResultRenderRequest(
            session_id=request.session_id,
            reply=reply,
            recommendations=recommendations,
            history=[
                *request.history,
                {"role": "user", "content": request.message},
                {"role": "assistant", "content": reply},
            ],
            intake={
                "fixed_reply_shortcut": True,
                "trigger": trigger,
            },
        )
    )


def _render_recommendation_cards(recommendations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rendered = render_agent_result(
        AgentResultRenderRequest(
            session_id="stream",
            recommendations=recommendations,
        )
    )
    return [card.model_dump() for card in rendered.cards]


def _render_done_event(session_id: str, data: dict[str, Any]) -> dict[str, Any]:
    rendered = render_agent_result(
        AgentResultRenderRequest(
            session_id=session_id,
            reply=data.get("reply"),
            agent_message=data.get("agent_message"),
            recommendations=data.get("recommendations", []),
            history=data.get("history", []),
            intake=data.get("intake", {}),
        )
    )
    return rendered.model_dump()


def _sse(event: str, data: Any) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False, separators=(',', ':'))}\n\n"
