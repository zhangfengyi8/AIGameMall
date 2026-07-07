from fastapi.testclient import TestClient

from app.main import app
from app.routers.agent_results import render_agent_result
from app.schemas.agent_results import AgentResultRenderRequest
from app.server import build_server_config


client = TestClient(app)


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
            "title": "钻石 · V4 · 5皮肤",
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
            "riskItems": ["防沉迷：NONE", "实名：SUPPORTED", "换绑：FULL_SUPPORTED"],
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
        assert user_message == "我想买安卓QQ 500以内的号"
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
            "message": "我想买安卓QQ 500以内的号",
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
        assert user_message == "我想买安卓QQ 500以内的号"
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
            "message": "我想买安卓QQ 500以内的号",
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


def test_account_detail_returns_frontend_detail_payload():
    response = client.get("/api/v1/accounts/listing_10019")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "listing_10019"
    assert body["account_id"] == "acc_100019"
    assert body["title"] == "高风险低价·不支持改实名皮肤号"
    assert body["price"] == 399
    assert body["platform"] == "QQ"
    assert body["server"] == "安卓QQ"
    assert body["rank"] == "钻石III"
    assert body["assets"]["skins"] == 102
    assert body["risk"]["level"] == "high"
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
