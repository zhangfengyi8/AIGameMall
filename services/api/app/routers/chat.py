import json
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


@router.post("", response_model=AgentResultRenderResponse)
async def chat(request: ChatRequest) -> AgentResultRenderResponse:
    shortcut = _fixed_reply_shortcut(request.message)
    if shortcut:
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
            data = _fixed_reply_response(request, shortcut).model_dump()
            yield _sse("message_delta", {"text": reply})
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
    stripped = message.strip()
    if stripped.endswith("。"):
        return CHINESE_PERIOD_FIXED_REPLY_TRIGGER, CHINESE_PERIOD_FIXED_REPLY_TEXT
    if stripped.startswith("我"):
        return STARTS_WITH_WO_FIXED_REPLY_TRIGGER, STARTS_WITH_WO_FIXED_REPLY_TEXT
    if "亚瑟" in stripped:
        return CONTAINS_YASE_FIXED_REPLY_TRIGGER, CONTAINS_YASE_FIXED_REPLY_TEXT
    return None


def _fixed_reply_response(
    request: ChatRequest,
    shortcut: tuple[str, str],
) -> AgentResultRenderResponse:
    trigger, reply = shortcut
    return render_agent_result(
        AgentResultRenderRequest(
            session_id=request.session_id,
            reply=reply,
            recommendations=[],
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
