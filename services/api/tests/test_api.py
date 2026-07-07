from fastapi.testclient import TestClient

from app.main import app
from app.server import build_server_config


client = TestClient(app)


def test_agent_result_render_returns_frontend_message_and_account_cards():
    response = client.post(
        "/api/v1/agent-results/render",
        json={
            "session_id": "session-001",
            "reply": "帮你筛选了安卓QQ区500元以内的账号，推荐以下账号。",
            "recommendations": [
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
            "history": [{"role": "assistant", "content": "帮你筛选了..."}],
            "intake": {"ready_for_recommendation": True},
        },
    )

    assert response.status_code == 200
    body = response.json()
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


def test_agent_result_render_returns_clarification_text_without_cards():
    response = client.post(
        "/api/v1/agent-results/render",
        json={
            "session_id": "session-002",
            "reply": "你想买安卓 QQ 还是微信区？预算大概是多少？",
            "recommendations": [],
            "history": [{"role": "assistant", "content": "你想买安卓 QQ 还是微信区？"}],
            "intake": {"ready_for_recommendation": False},
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "session_id": "session-002",
        "type": "clarification",
        "message": "你想买安卓 QQ 还是微信区？预算大概是多少？",
        "cards": [],
        "history": [{"role": "assistant", "content": "你想买安卓 QQ 还是微信区？"}],
        "intake": {"ready_for_recommendation": False},
    }


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


def test_server_config_runs_api_app_on_localhost():
    config = build_server_config()

    assert config.app == "app.main:app"
    assert config.host == "0.0.0.0"
    assert config.port == 8000
    assert config.reload is False
