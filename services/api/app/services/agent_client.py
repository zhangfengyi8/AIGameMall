import asyncio
import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Any, AsyncIterator


class AgentClientError(RuntimeError):
    pass


async def run_agent(user_message: str, history: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    agent_root = _repo_root() / "services" / "agent-orchestrator"
    if not agent_root.exists():
        raise AgentClientError("agent-orchestrator service not found")

    payload = json.dumps(
        {"message": user_message, "history": history or []},
        ensure_ascii=False,
    )
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    completed = await asyncio.to_thread(
        subprocess.run,
        [sys.executable, "-c", _AGENT_BRIDGE_SCRIPT],
        input=payload.encode("utf-8"),
        cwd=str(agent_root),
        capture_output=True,
        env=env,
        timeout=30,
    )
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise AgentClientError(detail or "agent process failed")

    return json.loads(completed.stdout.decode("utf-8"))


async def run_agent_stream(
    user_message: str,
    history: list[dict[str, Any]] | None = None,
) -> AsyncIterator[dict[str, Any]]:
    agent_root = _repo_root() / "services" / "agent-orchestrator"
    if not agent_root.exists():
        raise AgentClientError("agent-orchestrator service not found")

    payload = json.dumps(
        {"message": user_message, "history": history or []},
        ensure_ascii=False,
    )
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    process = await asyncio.to_thread(
        subprocess.Popen,
        [sys.executable, "-u", "-c", _AGENT_STREAM_BRIDGE_SCRIPT],
        cwd=str(agent_root),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    if process.stdin is None or process.stdout is None or process.stderr is None:
        raise AgentClientError("failed to open agent stream process")

    process.stdin.write(payload.encode("utf-8"))
    process.stdin.close()

    while True:
        line = await asyncio.to_thread(process.stdout.readline)
        if not line:
            break
        yield json.loads(line.decode("utf-8"))

    returncode = await asyncio.to_thread(process.wait, 30)
    if returncode != 0:
        stderr = await asyncio.to_thread(process.stderr.read)
        detail = stderr.decode("utf-8", errors="replace").strip()
        raise AgentClientError(detail or "agent stream process failed")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


_AGENT_BRIDGE_SCRIPT = textwrap.dedent(
    r"""
    import json
    import sys
    import types

    agents_module = types.ModuleType("agents")

    def function_tool(fn=None, *args, **kwargs):
        if callable(fn):
            return fn
        return lambda wrapped: wrapped

    agents_module.function_tool = function_tool
    sys.modules.setdefault("agents", agents_module)

    from app.schemas.detail import format_card
    from app.skills.requirement_intake import intake, search_params_from_intake
    from app.tools.search import _do_search

    payload = json.load(sys.stdin)
    message = payload["message"]
    history = payload.get("history") or []
    intake_result = intake(message)

    if not intake_result.get("ready_for_recommendation"):
        question = intake_result.get("clarifying_question") or "预算大概多少？最高能接受到多少？"
        reply = f"好的，我先了解下你的需求。{question}"
        result = {
            "reply": reply,
            "recommendations": [],
            "history": history + [
                {"role": "user", "content": message},
                {"role": "assistant", "content": reply},
            ],
            "intake": intake_result,
        }
    else:
        search_params = search_params_from_intake(intake_result)
        accounts = _do_search(**search_params)
        recommendations = [format_card(account) for account in accounts[:10]]
        if recommendations:
            reply = f"根据你的需求，为你推荐 {min(len(recommendations), 3)} 个账号。"
        else:
            reply = "抱歉，暂时没有找到完全符合你要求的账号。你可以试试放宽预算或者调整一下条件。"
        result = {
            "reply": reply,
            "recommendations": recommendations,
            "history": history + [
                {"role": "user", "content": message},
                {"role": "assistant", "content": reply},
            ],
            "intake": intake_result,
        }

    print(json.dumps(result, ensure_ascii=False))
    """
)


_AGENT_STREAM_BRIDGE_SCRIPT = textwrap.dedent(
    r"""
    import asyncio
    import json
    import os
    import sys
    import types

    def emit(event, data):
        print(json.dumps({"event": event, "data": data}, ensure_ascii=False), flush=True)

    payload = json.load(sys.stdin)
    message = payload["message"]
    history = payload.get("history") or []

    async def try_real_stream():
        if not os.environ.get("OPENAI_API_KEY"):
            return False
        try:
            from app.agent import run_agent_stream
        except Exception:
            return False
        async for event in run_agent_stream(message, history):
            emit(event["event"], event["data"])
        return True

    async def fallback_stream():
        agents_module = types.ModuleType("agents")

        def function_tool(fn=None, *args, **kwargs):
            if callable(fn):
                return fn
            return lambda wrapped: wrapped

        agents_module.function_tool = function_tool
        sys.modules.setdefault("agents", agents_module)

        from app.schemas.detail import format_card
        from app.skills.requirement_intake import intake, search_params_from_intake
        from app.tools.search import _do_search

        intake_result = intake(message)

        if not intake_result.get("ready_for_recommendation"):
            question = intake_result.get("clarifying_question") or "预算大概多少？最高能接受到多少？"
            reply = f"好的，我先了解下你的需求。{question}"
            for char in reply:
                emit("message_delta", {"text": char})
            emit(
                "done",
                {
                    "reply": reply,
                    "recommendations": [],
                    "history": history + [
                        {"role": "user", "content": message},
                        {"role": "assistant", "content": reply},
                    ],
                    "intake": intake_result,
                },
            )
            return

        search_params = search_params_from_intake(intake_result)
        accounts = _do_search(**search_params)
        recommendations = [format_card(account) for account in accounts[:10]]
        emit(
            "strategy",
            {
                "filters": search_params,
                "account_count": len(accounts),
                "account_ids": [account.get("listingId", "") for account in accounts[:10]],
            },
        )
        if recommendations:
            reply = f"根据你的需求，为你推荐 {min(len(recommendations), 3)} 个账号。"
        else:
            reply = "抱歉，暂时没有找到完全符合你要求的账号。你可以试试放宽预算或者调整一下条件。"
        for char in reply:
            emit("message_delta", {"text": char})
        emit("recommendations", recommendations)
        emit(
            "done",
            {
                "reply": reply,
                "recommendations": recommendations,
                "history": history + [
                    {"role": "user", "content": message},
                    {"role": "assistant", "content": reply},
                ],
                "intake": intake_result,
            },
        )

    async def main():
        if not await try_real_stream():
            await fallback_stream()

    asyncio.run(main())
    """
)
