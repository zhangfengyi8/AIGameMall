import asyncio
import sys
import types
from pathlib import Path

agents_module = types.ModuleType("agents")


class _Agent:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


_LLM_CHAT_REPLY = "哈哈猜不到呀，不过想找号随时喊我～"


class _FakeResult:
    final_output = _LLM_CHAT_REPLY

    def to_input_list(self):
        return []


class _FakeStreamResult:
    async def stream_events(self):
        return
        yield  # pragma: no cover - makes this an async generator

    def to_input_list(self):
        return []


class _Runner:
    run_calls = 0
    stream_calls = 0

    @staticmethod
    async def run(*args, **kwargs):
        _Runner.run_calls += 1
        return _FakeResult()

    @staticmethod
    def run_streamed(*args, **kwargs):
        _Runner.stream_calls += 1
        return _FakeStreamResult()


agents_module.Agent = _Agent
agents_module.Runner = _Runner
agents_module.set_tracing_disabled = lambda *_args, **_kwargs: None
agents_module.function_tool = lambda fn=None, *args, **kwargs: fn if callable(fn) else (lambda wrapped: wrapped)
sys.modules["agents"] = agents_module

responses_module = types.ModuleType("agents.models.openai_responses")
responses_module.OpenAIResponsesModel = lambda *args, **kwargs: object()
sys.modules["agents.models"] = types.ModuleType("agents.models")
sys.modules["agents.models.openai_responses"] = responses_module

openai_module = types.ModuleType("openai")
openai_module.AsyncOpenAI = lambda *args, **kwargs: object()
sys.modules["openai"] = openai_module

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agent import run_agent, run_agent_stream


def test_run_agent_identity_question_returns_controlled_reply_without_recommendations():
    before = _Runner.run_calls
    result = asyncio.run(run_agent("你是谁", []))

    assert result["recommendations"] == []
    assert result["history"] == [{"role": "user", "content": "你是谁"}, {"role": "assistant", "content": result["reply"]}]
    assert result["intake"]["intent"] == "assistant_identity"
    assert "智能导购助手" in result["reply"]
    # 身份问题走受控固定回复，不调用 LLM
    assert _Runner.run_calls == before


def test_run_agent_unknown_message_gets_natural_llm_chat():
    before = _Runner.run_calls
    result = asyncio.run(run_agent("你猜我是谁", []))

    assert result["recommendations"] == []
    assert result["intake"]["intent"] == "unknown"
    # 无法识别的消息交给 LLM 自然回复
    assert _Runner.run_calls == before + 1
    assert result["reply"] == _LLM_CHAT_REPLY


def test_run_agent_not_buying_respects_user_choice():
    history = [
        {"role": "user", "content": "帮我找孙尚香荣耀典藏账号"},
        {"role": "assistant", "content": "预算大概多少？你用 QQ 还是微信，安卓还是 iOS？"},
    ]

    before = _Runner.run_calls
    result = asyncio.run(run_agent("不买了", history))

    assert result["recommendations"] == []
    assert result["intake"]["intent"] == "not_buying"
    assert "没问题" in result["reply"]
    # 拒买属于受控回复，不调用 LLM
    assert _Runner.run_calls == before


def test_run_agent_stream_controlled_reply_emits_no_recommendations():
    async def collect_events():
        return [event async for event in run_agent_stream("你是谁", [])]

    events = asyncio.run(collect_events())

    assert events[0] == {"event": "message_delta", "data": {"text": "我是你的游戏账号智能导购助手，可以按预算、区服、英雄皮肤、段位和风险偏好帮你筛选账号。"}}
    assert events[1] == {"event": "recommendations", "data": []}
    assert events[2]["event"] == "done"
    assert events[2]["data"]["recommendations"] == []
    assert events[2]["data"]["intake"]["intent"] == "assistant_identity"
