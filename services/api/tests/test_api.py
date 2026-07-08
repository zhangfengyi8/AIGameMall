import asyncio
import shutil
import uuid
from pathlib import Path

from fastapi.testclient import TestClient

from app.services import agent_client
from app.main import app
from app.routers.agent_results import render_agent_result
from app.schemas.agent_results import AgentResultRenderRequest
from app.server import build_server_config


client = TestClient(app)


def make_test_repo_root():
    root = Path.cwd() / ".test-tmp" / uuid.uuid4().hex
    root.mkdir(parents=True)
    return root


def test_agent_client_calls_agent_module_run_agent(monkeypatch):
    tmp_path = make_test_repo_root()
    agent_dir = tmp_path / "services" / "agent-orchestrator" / "app"
    try:
        agent_dir.mkdir(parents=True)
        (agent_dir / "__init__.py").write_text("", encoding="utf-8")
        (agent_dir / "agent.py").write_text(
            """
async def run_agent(user_message, history):
    return {
        "reply": f"real:{user_message}",
        "recommendations": [],
        "history": history + [{"role": "assistant", "content": "real"}],
        "intake": {"source": "real-agent"},
    }
""",
            encoding="utf-8",
        )
        monkeypatch.setattr(agent_client, "_repo_root", lambda: tmp_path)

        result = asyncio.run(agent_client.run_agent("hello", [{"role": "user", "content": "old"}]))

        assert result["reply"] == "real:hello"
        assert result["intake"] == {"source": "real-agent"}
        assert result["history"] == [
            {"role": "user", "content": "old"},
            {"role": "assistant", "content": "real"},
        ]
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)


def test_agent_client_calls_agent_module_run_agent_stream(monkeypatch):
    tmp_path = make_test_repo_root()
    agent_dir = tmp_path / "services" / "agent-orchestrator" / "app"
    try:
        agent_dir.mkdir(parents=True)
        (agent_dir / "__init__.py").write_text("", encoding="utf-8")
        (agent_dir / "agent.py").write_text(
            """
async def run_agent_stream(user_message, history):
    yield {"event": "message_delta", "data": {"text": f"real:{user_message}"}}
    yield {
        "event": "done",
        "data": {
            "reply": "done",
            "recommendations": [],
            "history": history,
            "intake": {"source": "real-agent-stream"},
        },
    }
""",
            encoding="utf-8",
        )
        monkeypatch.setattr(agent_client, "_repo_root", lambda: tmp_path)

        async def collect():
            return [event async for event in agent_client.run_agent_stream("hello", [])]

        events = asyncio.run(collect())

        assert events == [
            {"event": "message_delta", "data": {"text": "real:hello"}},
            {
                "event": "done",
                "data": {
                    "reply": "done",
                    "recommendations": [],
                    "history": [],
                    "intake": {"source": "real-agent-stream"},
                },
            },
        ]
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)


def test_agent_result_renderer_returns_frontend_message_and_account_cards():
    response = render_agent_result(
        AgentResultRenderRequest(
            session_id="session-001",
            reply="帮你筛选了安卓QQ区500元以内的账号，推荐以下账号。",
            recommendations=[
                {
                    "account_id": "listing_10019",
                    "accountId": "acc_100019",
                    "game_code": "WZ",
                    "server_code": "ANDROID_QQ",
                    "price": 399,
                    "vip_level": 4,
                    "rank_name": "钻石",
                    "rank_stars": 0,
                    "anti_addiction": "NONE",
                    "secondary_real_name": "SUPPORTED",
                    "change_bind": "FULL_SUPPORTED",
                    "skin_count": 5,
                    "hero_count": 5,
                    "value_score": 101.55,
                    "heroes": ["孙悟空", "李白"],
                    "skins": ["地狱火", "白龙吟"],
                }
            ],
            history=[{"role": "assistant", "content": "帮你筛选了..."}],
            intake={"ready_for_recommendation": True},
        )
    )

    body = response.model_dump()
    assert body["session_id"] == "session-001"
    assert body["type"] == "recommendations"
    assert body["message"] == "帮你筛选了安卓QQ区500元以内的账号，推荐以下账号。"
    assert body["history"] == [{"role": "assistant", "content": "帮你筛选了..."}]
    assert body["intake"] == {"ready_for_recommendation": True}
    assert body["cards"] == [
        {
            "id": "listing_10019",
            "title": "钻石 · V4",
            "price": 399,
            "match": 100,
            "heroes": 5,
            "skins": 5,
            "rank": "钻石",
            "vip": 4,
            "region": "安卓QQ",
            "estValue": 399,
            "estLabel": "高性价比",
            "risk": "低",
            "riskItems": ["防沉迷：无", "实名：支持", "换绑：支持"],
            "highlightSkins": ["地狱火", "白龙吟"],
            "detail_api": "/api/v1/accounts/listing_10019",
        }
    ]


def test_agent_result_renderer_returns_clarification_text_without_cards():
    response = render_agent_result(
        AgentResultRenderRequest(
            session_id="session-002",
            reply="你想买安卓 QQ 还是微信区？预算大概是多少？",
            recommendations=[],
            history=[{"role": "assistant", "content": "你想买安卓 QQ 还是微信区？"}],
            intake={"ready_for_recommendation": False},
        )
    )

    assert response.model_dump() == {
        "session_id": "session-002",
        "type": "clarification",
        "message": "你想买安卓 QQ 还是微信区？预算大概是多少？",
        "cards": [],
        "history": [{"role": "assistant", "content": "你想买安卓 QQ 还是微信区？"}],
        "intake": {"ready_for_recommendation": False},
    }


def test_chat_calls_agent_and_returns_frontend_cards(monkeypatch):
    async def fake_run_agent(user_message, history):
        assert user_message == "想买安卓QQ 500以内的号"
        assert history == [{"role": "assistant", "content": "之前的回复"}]
        return {
            "reply": "为你推荐 1 个账号。",
            "recommendations": [
                {
                    "account_id": "listing_10019",
                    "server_code": "ANDROID_QQ",
                    "price": 399,
                    "vip_level": 4,
                    "rank_name": "钻石",
                    "rank_stars": 0,
                    "anti_addiction": "NONE",
                    "secondary_real_name": "SUPPORTED",
                    "change_bind": "FULL_SUPPORTED",
                    "skin_count": 5,
                    "hero_count": 5,
                    "value_score": 99,
                    "skins": ["地狱火"],
                }
            ],
            "history": [{"role": "assistant", "content": "为你推荐 1 个账号。"}],
            "intake": {"ready_for_recommendation": True},
        }

    monkeypatch.setattr("app.routers.chat.run_agent", fake_run_agent)

    response = client.post(
        "/api/v1/chat",
        json={
            "session_id": "session-chat-001",
            "message": "想买安卓QQ 500以内的号",
            "history": [{"role": "assistant", "content": "之前的回复"}],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["session_id"] == "session-chat-001"
    assert body["type"] == "recommendations"
    assert body["message"] == "为你推荐 1 个账号。"
    assert body["cards"][0]["id"] == "listing_10019"
    assert body["cards"][0]["detail_api"] == "/api/v1/accounts/listing_10019"
    assert body["history"] == [{"role": "assistant", "content": "为你推荐 1 个账号。"}]
    assert body["intake"] == {"ready_for_recommendation": True}


def test_chat_returns_fixed_reply_when_message_ends_with_chinese_period(monkeypatch):
    async def fail_if_called(_user_message, _history):
        raise AssertionError("agent should not be called for fixed reply shortcut")

    sleep_calls = []

    async def fake_sleep(seconds):
        sleep_calls.append(seconds)

    monkeypatch.setattr("app.routers.chat.run_agent", fail_if_called)
    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    monkeypatch.setenv("AIGAMEMALL_ENABLE_FIXED_REPLIES", "true")

    response = client.post(
        "/api/v1/chat",
        json={
            "session_id": "session-chat-fixed-reply",
            "message": "需要全皮肤的账号，微信区，安卓平台。",
            "history": [{"role": "assistant", "content": "上一轮"}],
        },
    )

    assert response.status_code == 200
    body = response.json()
    fixed_reply = (
        "可以，我帮你筛到三个符合方向的账号：安卓微信区，高皮肤覆盖账号，适合想要"
        "“全皮肤体验”的玩家。这三个号皮肤数量都很高，热门英雄常用皮肤覆盖比较完整，"
        "限定和高品质皮肤也比较丰富，适合收藏和日常排位使用。交易条件方面，账号支持"
        "换绑和二次实名，防沉迷状态正常，整体风险较低。综合来看，如果你主要想要安卓"
        "微信区、皮肤尽量齐全的账号，这三个号可以作为优先选择。"
    )
    assert body == {
        "session_id": "session-chat-fixed-reply",
        "type": "recommendations",
        "message": fixed_reply,
        "cards": [
            {
                "id": "listing_10005",
                "title": "荣耀王者56星 · V9 · 389皮肤",
                "price": 4980,
                "match": 98,
                "heroes": 120,
                "skins": 389,
                "rank": "荣耀王者56星",
                "vip": 9,
                "region": "安卓微信",
                "estValue": 4980,
                "estLabel": "高性价比",
                "risk": "低",
                "riskItems": ["防沉迷：无", "实名：支持", "换绑：支持"],
                "highlightSkins": ["全息碎影", "凤求凰", "至尊宝"],
                "detail_api": "/api/v1/accounts/listing_10005",
            },
            {
                "id": "listing_10015",
                "title": "无双王者42星 · V8 · 372皮肤",
                "price": 4680,
                "match": 95,
                "heroes": 118,
                "skins": 372,
                "rank": "无双王者42星",
                "vip": 8,
                "region": "安卓微信",
                "estValue": 4680,
                "estLabel": "高性价比",
                "risk": "低",
                "riskItems": ["防沉迷：无", "实名：支持", "换绑：支持"],
                "highlightSkins": ["倪克斯神谕", "天鹅之梦", "白龙吟"],
                "detail_api": "/api/v1/accounts/listing_10015",
            },
            {
                "id": "listing_10003",
                "title": "王者30星 · V8 · 358皮肤",
                "price": 4380,
                "match": 92,
                "heroes": 116,
                "skins": 358,
                "rank": "王者30星",
                "vip": 8,
                "region": "安卓微信",
                "estValue": 4380,
                "estLabel": "高性价比",
                "risk": "低",
                "riskItems": ["防沉迷：无", "实名：支持", "换绑：支持"],
                "highlightSkins": ["地狱火", "末日机甲", "遇见神鹿"],
                "detail_api": "/api/v1/accounts/listing_10003",
            },
        ],
        "history": [
            {"role": "assistant", "content": "上一轮"},
            {"role": "user", "content": "需要全皮肤的账号，微信区，安卓平台。"},
            {"role": "assistant", "content": fixed_reply},
        ],
        "intake": {
            "fixed_reply_shortcut": True,
            "trigger": "message_endswith_chinese_period",
        },
    }
    assert sleep_calls == [5]


def test_chat_returns_fixed_reply_when_message_starts_with_wo(monkeypatch):
    async def fail_if_called(_user_message, _history):
        raise AssertionError("agent should not be called for fixed reply shortcut")

    sleep_calls = []

    async def fake_sleep(seconds):
        sleep_calls.append(seconds)

    monkeypatch.setattr("app.routers.chat.run_agent", fail_if_called)
    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    monkeypatch.setenv("AIGAMEMALL_ENABLE_FIXED_REPLIES", "true")
    monkeypatch.setenv("AIGAMEMALL_ENABLE_FIXED_REPLIES", "true")

    response = client.post(
        "/api/v1/chat",
        json={
            "session_id": "session-chat-fixed-reply-starts-with-wo",
            "message": "我想买一个适合收藏的账号",
            "history": [],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["message"].startswith("可以，我帮你筛到三个符合方向的账号")
    assert "适合根据你的预算、平台和偏好继续筛选" in body["message"]
    assert body["type"] == "recommendations"
    assert [card["id"] for card in body["cards"]] == [
        "listing_10019",
        "listing_10014",
        "listing_10013",
    ]
    assert body["history"][-2:] == [
        {"role": "user", "content": "我想买一个适合收藏的账号"},
        {"role": "assistant", "content": body["message"]},
    ]
    assert body["intake"] == {
        "fixed_reply_shortcut": True,
        "trigger": "message_startswith_wo",
    }
    assert sleep_calls == [5]


def test_chat_specific_skin_request_calls_agent_instead_of_fixed_reply(monkeypatch):
    agent_calls = []

    async def fake_run_agent(user_message, history):
        agent_calls.append((user_message, history))
        return {
            "reply": "真实 agent 返回",
            "recommendations": [
                {
                    "account_id": "listing_10001",
                    "server_code": "ANDROID_QQ",
                    "price": 4200,
                    "vip_level": 8,
                    "rank_name": "王者",
                    "rank_stars": 13,
                    "anti_addiction": "NONE",
                    "secondary_real_name": "SUPPORTED",
                    "change_bind": "FULL_SUPPORTED",
                    "skin_count": 286,
                    "hero_count": 115,
                    "value_score": 94,
                    "skins": ["杀手不太冷"],
                }
            ],
            "history": [{"role": "assistant", "content": "真实 agent 返回"}],
            "intake": {"ready_for_recommendation": True},
        }

    monkeypatch.setattr("app.routers.chat.run_agent", fake_run_agent)

    response = client.post(
        "/api/v1/chat",
        json={
            "session_id": "session-specific-skin",
            "message": "我想买带孙尚香典藏皮肤的账号",
            "history": [],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert agent_calls == [("我想买带孙尚香典藏皮肤的账号", [])]
    assert body["message"] == "真实 agent 返回"
    assert body["cards"][0]["id"] == "listing_10001"
    assert body["cards"][0]["highlightSkins"] == ["杀手不太冷"]
    assert body["intake"] == {"ready_for_recommendation": True}


def test_chat_returns_fixed_reply_when_message_contains_yase(monkeypatch):
    async def fail_if_called(_user_message, _history):
        raise AssertionError("agent should not be called for fixed reply shortcut")

    sleep_calls = []

    async def fake_sleep(seconds):
        sleep_calls.append(seconds)

    monkeypatch.setattr("app.routers.chat.run_agent", fail_if_called)
    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    monkeypatch.setenv("AIGAMEMALL_ENABLE_FIXED_REPLIES", "true")

    response = client.post(
        "/api/v1/chat",
        json={
            "session_id": "session-chat-fixed-reply-contains-yase",
            "message": "帮我找一个有亚瑟的账号",
            "history": [],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["message"].startswith("可以，我帮你筛到三个符合方向的账号")
    assert "亚瑟" in body["message"]
    assert body["type"] == "recommendations"
    assert [card["id"] for card in body["cards"]] == [
        "listing_10005",
        "listing_10012",
        "listing_10019",
    ]
    assert body["history"][-2:] == [
        {"role": "user", "content": "帮我找一个有亚瑟的账号"},
        {"role": "assistant", "content": body["message"]},
    ]
    assert body["intake"] == {
        "fixed_reply_shortcut": True,
        "trigger": "message_contains_yase",
    }
    assert sleep_calls == [5]


def test_chat_returns_fixed_reply_when_message_is_change_batch(monkeypatch):
    async def fail_if_called(_user_message, _history):
        raise AssertionError("agent should not be called for fixed reply shortcut")

    sleep_calls = []

    async def fake_sleep(seconds):
        sleep_calls.append(seconds)

    monkeypatch.setattr("app.routers.chat.run_agent", fail_if_called)
    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    monkeypatch.setenv("AIGAMEMALL_ENABLE_FIXED_REPLIES", "true")

    response = client.post(
        "/api/v1/chat",
        json={
            "session_id": "session-chat-fixed-reply-change-batch",
            "message": "换一批",
            "history": [{"role": "assistant", "content": "上一批推荐"}],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["type"] == "recommendations"
    assert body["message"].startswith("好的，我重新给你换一批账号")
    assert "这几个号和上一批侧重点不一样" in body["message"]
    assert [card["id"] for card in body["cards"]] == [
        "listing_10002",
        "listing_10008",
        "listing_10011",
    ]
    assert body["history"][-2:] == [
        {"role": "user", "content": "换一批"},
        {"role": "assistant", "content": body["message"]},
    ]
    assert body["intake"] == {
        "fixed_reply_shortcut": True,
        "trigger": "message_change_batch",
    }
    assert sleep_calls == [5]


def test_chat_change_batch_calls_agent_when_fixed_replies_are_disabled(monkeypatch):
    agent_calls = []

    async def fake_run_agent(user_message, history):
        agent_calls.append((user_message, history))
        return {
            "reply": "真实 agent 换一批返回",
            "recommendations": [],
            "history": [{"role": "assistant", "content": "真实 agent 换一批返回"}],
            "intake": {"source": "real-agent"},
        }

    monkeypatch.delenv("AIGAMEMALL_ENABLE_FIXED_REPLIES", raising=False)
    monkeypatch.setattr("app.routers.chat.run_agent", fake_run_agent)

    response = client.post(
        "/api/v1/chat",
        json={
            "session_id": "session-chat-change-batch-real-agent",
            "message": "换一批",
            "history": [{"role": "assistant", "content": "上一批推荐"}],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert agent_calls == [("换一批", [{"role": "assistant", "content": "上一批推荐"}])]
    assert body["message"] == "真实 agent 换一批返回"
    assert body["cards"] == []
    assert body["intake"] == {"source": "real-agent"}


def test_fixed_reply_card_detail_apis_use_existing_accounts(monkeypatch):
    async def fake_sleep(_seconds):
        return None

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    monkeypatch.setenv("AIGAMEMALL_ENABLE_FIXED_REPLIES", "true")

    for message in [
        "需要全皮肤的账号，微信区，安卓平台。",
        "我想买一个适合收藏的账号",
        "帮我找一个有亚瑟的账号",
        "换一批",
    ]:
        response = client.post(
            "/api/v1/chat",
            json={
                "session_id": f"session-detail-check-{message[:1]}",
                "message": message,
                "history": [],
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert len(body["cards"]) == 3
        for card in body["cards"]:
            detail_response = client.get(card["detail_api"])
            assert detail_response.status_code == 200
            assert detail_response.json()["id"] == card["id"]


def test_chat_returns_502_when_agent_fails(monkeypatch):
    async def fake_run_agent(_user_message, _history):
        raise RuntimeError("agent unavailable")

    monkeypatch.setattr("app.routers.chat.run_agent", fake_run_agent)

    response = client.post(
        "/api/v1/chat",
        json={
            "session_id": "session-chat-002",
            "message": "帮我推荐账号",
        },
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "Agent service unavailable"


def test_chat_stream_returns_sse_events(monkeypatch):
    async def fake_run_agent_stream(user_message, history):
        assert user_message == "想买安卓QQ 500以内的号"
        assert history == []
        yield {"event": "message_delta", "data": {"text": "为你"}}
        yield {"event": "message_delta", "data": {"text": "推荐"}}
        yield {
            "event": "recommendations",
            "data": [
                {
                    "account_id": "listing_10019",
                    "server_code": "ANDROID_QQ",
                    "price": 399,
                    "vip_level": 4,
                    "rank_name": "钻石",
                    "rank_stars": 0,
                    "anti_addiction": "NONE",
                    "secondary_real_name": "SUPPORTED",
                    "change_bind": "FULL_SUPPORTED",
                    "skin_count": 5,
                    "hero_count": 5,
                    "value_score": 99,
                    "skins": ["地狱火"],
                }
            ],
        }
        yield {
            "event": "done",
            "data": {
                "reply": "为你推荐",
                "recommendations": [
                    {
                        "account_id": "listing_10019",
                        "server_code": "ANDROID_QQ",
                        "price": 399,
                        "vip_level": 4,
                        "rank_name": "钻石",
                        "rank_stars": 0,
                        "anti_addiction": "NONE",
                        "secondary_real_name": "SUPPORTED",
                        "change_bind": "FULL_SUPPORTED",
                        "skin_count": 5,
                        "hero_count": 5,
                        "value_score": 99,
                        "skins": ["地狱火"],
                    }
                ],
                "history": [{"role": "assistant", "content": "为你推荐"}],
                "intake": {"ready_for_recommendation": True},
            },
        }

    monkeypatch.setattr("app.routers.chat.run_agent_stream", fake_run_agent_stream)

    response = client.post(
        "/api/v1/chat/stream",
        json={
            "session_id": "session-stream-001",
            "message": "想买安卓QQ 500以内的号",
            "history": [],
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    body = response.text
    assert 'event: message_delta\ndata: {"text":"为你"}' in body
    assert 'event: message_delta\ndata: {"text":"推荐"}' in body
    assert 'event: recommendations\ndata: [{"id":"listing_10019"' in body
    assert 'event: done\ndata: {"session_id":"session-stream-001","type":"recommendations"' in body


def test_chat_stream_returns_fixed_reply_when_message_ends_with_chinese_period(monkeypatch):
    async def fail_if_called(_user_message, _history):
        raise AssertionError("agent stream should not be called for fixed reply shortcut")
        yield

    sleep_calls = []

    async def fake_sleep(seconds):
        sleep_calls.append(seconds)

    monkeypatch.setattr("app.routers.chat.run_agent_stream", fail_if_called)
    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    monkeypatch.setenv("AIGAMEMALL_ENABLE_FIXED_REPLIES", "true")

    response = client.post(
        "/api/v1/chat/stream",
        json={
            "session_id": "session-stream-fixed-reply",
            "message": "需要全皮肤的账号，微信区，安卓平台。",
            "history": [],
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    body = response.text
    assert "event: message_delta" in body
    assert "可以，我帮你筛到三个符合方向的账号" in body
    assert "event: recommendations" in body
    assert '"id":"listing_10005"' in body
    assert "event: done" in body
    assert '"session_id":"session-stream-fixed-reply"' in body
    assert '"fixed_reply_shortcut":true' in body
    assert sleep_calls == [5]


def test_chat_stream_returns_fixed_reply_when_message_is_change_batch(monkeypatch):
    async def fail_if_called(_user_message, _history):
        raise AssertionError("agent stream should not be called for fixed reply shortcut")
        yield

    sleep_calls = []

    async def fake_sleep(seconds):
        sleep_calls.append(seconds)

    monkeypatch.setattr("app.routers.chat.run_agent_stream", fail_if_called)
    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    monkeypatch.setenv("AIGAMEMALL_ENABLE_FIXED_REPLIES", "true")

    response = client.post(
        "/api/v1/chat/stream",
        json={
            "session_id": "session-stream-fixed-reply-change-batch",
            "message": "换一批",
            "history": [],
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    body = response.text
    assert "event: message_delta" in body
    assert "好的，我重新给你换一批账号" in body
    assert "event: recommendations" in body
    assert '"id":"listing_10002"' in body
    assert '"id":"listing_10008"' in body
    assert '"id":"listing_10011"' in body
    assert "event: done" in body
    assert '"trigger":"message_change_batch"' in body
    assert sleep_calls == [5]


def test_account_detail_returns_frontend_detail_payload():
    response = client.get("/api/v1/accounts/listing_10019")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "listing_10019"
    assert body["account_id"] == "acc_100019"
    assert body["title"] == "安卓QQ · 钻石 · V4 · 5皮肤账号"
    assert body["price"] == 399
    assert body["platform"] == "QQ"
    assert body["server"] == "安卓QQ"
    assert body["rank"] == "钻石"
    assert body["assets"]["skins"] == 5
    assert body["assets"]["heroes"] == 5
    assert body["assets"]["rare_skins"] == ["地狱火", "白龙吟", "精灵王", "女仆咖啡", "狮心王"]
    assert body["risk"]["level"] == "low"
    assert body["risk"]["notes"] == ["无防沉迷", "支持二次实名", "支持换绑"]
    assert body["purchase_tips"]


def test_account_detail_returns_404_for_unknown_account():
    response = client.get("/api/v1/accounts/not-exist")

    assert response.status_code == 404
    assert response.json()["detail"] == "Account not found"


def test_removed_api_surface_is_not_exposed():
    assert client.get("/health").status_code == 404
    assert client.get("/api/v1/guide/home").status_code == 404
    assert client.get("/api/v1/skins").status_code == 404
    assert client.post("/api/v1/agent-results/render", json={}).status_code == 404


def test_server_config_runs_api_app_on_localhost():
    config = build_server_config()

    assert config.app == "app.main:app"
    assert config.host == "0.0.0.0"
    assert config.port == 8000
    assert config.reload is False
