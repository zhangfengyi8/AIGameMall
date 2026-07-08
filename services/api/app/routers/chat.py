import json
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.routers.agent_results import render_agent_result
from app.schemas.agent_results import AgentResultRenderRequest, AgentResultRenderResponse
from app.schemas.chat import ChatRequest
from app.services.agent_client import AgentClientError, run_agent, run_agent_stream


router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=AgentResultRenderResponse)
async def chat(request: ChatRequest) -> AgentResultRenderResponse:
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
