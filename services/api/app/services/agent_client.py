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
    import asyncio
    import json
    import os
    import sys

    payload = json.load(sys.stdin)
    message = payload["message"]
    history = payload.get("history") or []

    async def call_real_agent():
        from app.agent import run_agent
        return await run_agent(message, history)

    def call_agent_fallback():
        import types
        agents_module = types.ModuleType("agents")

        def function_tool(fn=None, *args, **kwargs):
            if callable(fn):
                return fn
            return lambda wrapped: wrapped

        agents_module.function_tool = function_tool
        sys.modules.setdefault("agents", agents_module)

        from app.fallback.rule_engine import run_fallback
        result = run_fallback(message, history)
        result.setdefault("recommendations", [])
        result.setdefault("intake", {})
        return result

    try:
        result = asyncio.run(call_real_agent())
    except Exception:
        result = call_agent_fallback()

    print(json.dumps(result, ensure_ascii=False))
    """
)


_AGENT_STREAM_BRIDGE_SCRIPT = textwrap.dedent(
    r"""
    import asyncio
    import json
    import sys

    def emit(event, data):
        print(json.dumps({"event": event, "data": data}, ensure_ascii=False), flush=True)

    payload = json.load(sys.stdin)
    message = payload["message"]
    history = payload.get("history") or []

    async def real_stream():
        from app.agent import run_agent_stream
        async for event in run_agent_stream(message, history):
            emit(event["event"], event["data"])

    async def fallback_stream():
        import types
        agents_module = types.ModuleType("agents")

        def function_tool(fn=None, *args, **kwargs):
            if callable(fn):
                return fn
            return lambda wrapped: wrapped

        agents_module.function_tool = function_tool
        sys.modules.setdefault("agents", agents_module)

        from app.fallback.rule_engine import run_fallback
        result = run_fallback(message, history)
        reply = result.get("reply", "")
        for char in reply:
            emit("message_delta", {"text": char})
        emit(
            "done",
            {
                "reply": reply,
                "recommendations": result.get("recommendations", []),
                "history": result.get("history", history),
                "intake": result.get("intake", {}),
            },
        )

    async def main():
        try:
            await real_stream()
        except Exception:
            await fallback_stream()

    asyncio.run(main())
    """
)
