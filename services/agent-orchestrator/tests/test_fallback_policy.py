import sys
import types
from pathlib import Path

agents_module = types.ModuleType("agents")
agents_module.function_tool = lambda fn=None, *args, **kwargs: fn if callable(fn) else (lambda wrapped: wrapped)
sys.modules.setdefault("agents", agents_module)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.fallback import rule_engine


def _account(listing_id: str) -> dict:
    return {
        "listingId": listing_id,
        "serverCode": "ANDROID_QQ",
        "salePrice": 1000,
        "vipLevel": 5,
        "rankName": "王者",
        "rankStars": 1,
        "antiAddictionStatus": "NONE",
        "secondaryRealNameStatus": "SUPPORTED",
        "changeBindStatus": "FULL_SUPPORTED",
    }


def test_fallback_returns_no_cards_and_clear_message_when_no_matches(monkeypatch):
    monkeypatch.setattr(rule_engine, "_do_search", lambda **_params: [])

    result = rule_engine.run_fallback("预算2000，安卓QQ，孙尚香荣耀典藏")

    assert result["recommendations"] == []
    assert "暂时找不到相关账号，换个条件试试吧" in result["reply"]


def test_fallback_keeps_actual_count_when_less_than_three(monkeypatch):
    accounts = [_account("listing_10008")]
    monkeypatch.setattr(rule_engine, "_do_search", lambda **_params: accounts)
    monkeypatch.setattr(
        rule_engine,
        "_do_load",
        lambda filename: {
            "accountMetrics.json": [{"listingId": "listing_10008", "skinCount": 100, "heroCount": 80, "valueScore": 90}],
            "skinMaster.json": [{"skinId": "skin_1", "skinName": "杀手不太冷"}],
            "accountSkin.json": [{"listingId": "listing_10008", "skinId": "skin_1"}],
        }[filename],
    )

    result = rule_engine.run_fallback("预算2000，安卓QQ，孙尚香荣耀典藏")

    assert len(result["recommendations"]) == 1
    assert result["recommendations"][0]["account_id"] == "listing_10008"
    assert result["reply"].startswith("找到一个比较匹配的账号，可以优先看看。")
    assert "推荐一" in result["reply"]
    assert "整体描述" not in result["reply"]
    assert "不硬凑" not in result["reply"]
    assert "数量不足" not in result["reply"]
    assert "listing_10008" not in result["reply"]
    assert "ANDROID_QQ" not in result["reply"]
    assert "这几款" not in result["reply"]
    assert "下单前注意事项" in result["reply"]


def test_fallback_caps_recommendations_at_three(monkeypatch):
    accounts = [_account(f"listing_1000{i}") for i in range(1, 6)]
    monkeypatch.setattr(rule_engine, "_do_search", lambda **_params: accounts)
    monkeypatch.setattr(
        rule_engine,
        "_do_load",
        lambda filename: {
            "accountMetrics.json": [
                {"listingId": account["listingId"], "skinCount": 100, "heroCount": 80, "valueScore": 90}
                for account in accounts
            ],
            "skinMaster.json": [],
            "accountSkin.json": [],
        }[filename],
    )

    result = rule_engine.run_fallback("预算2000，安卓QQ")

    assert [item["account_id"] for item in result["recommendations"]] == [
        "listing_10001",
        "listing_10002",
        "listing_10003",
    ]
    assert result["reply"].startswith("我筛到几款比较接近你需求的账号，可以按优先级看看：")
    assert "推荐一" in result["reply"]
    assert "推荐二" in result["reply"]
    assert "推荐三" in result["reply"]
    assert "整体描述" not in result["reply"]
    assert "不硬凑" not in result["reply"]
    assert "数量不足" not in result["reply"]
    assert "listing_" not in result["reply"]
    assert "ANDROID_QQ" not in result["reply"]



def test_fallback_uses_single_shared_risk_note_for_multiple_recommendations(monkeypatch):
    accounts = [_account("listing_10001"), _account("listing_10002")]
    monkeypatch.setattr(rule_engine, "_do_search", lambda **_params: accounts)
    monkeypatch.setattr(
        rule_engine,
        "_do_load",
        lambda filename: {
            "accountMetrics.json": [
                {"listingId": "listing_10001", "skinCount": 100, "heroCount": 80, "valueScore": 90},
                {"listingId": "listing_10002", "skinCount": 120, "heroCount": 90, "valueScore": 88},
            ],
            "skinMaster.json": [
                {"skinId": "skin_1", "skinName": "杀手不太冷"},
                {"skinId": "skin_2", "skinName": "末日机甲"},
            ],
            "accountSkin.json": [
                {"listingId": "listing_10001", "skinId": "skin_1"},
                {"listingId": "listing_10002", "skinId": "skin_2"},
            ],
        }[filename],
    )

    result = rule_engine.run_fallback("预算5000，安卓QQ，孙尚香")

    assert result["reply"].count("下单前建议") == 1
    assert result["reply"].count("交易安全上") == 1
    assert result["reply"].count("性价比不错") <= 1



def test_fallback_current_budget_overrides_older_history_budget(monkeypatch):
    accounts = [_account("listing_10008"), _account("listing_10001")]
    accounts[0]["salePrice"] = 980
    accounts[1]["salePrice"] = 4200

    def fake_search(**params):
        budget_max = params.get("budget_max")
        if budget_max is None:
            return accounts
        return [account for account in accounts if account["salePrice"] <= budget_max]

    monkeypatch.setattr(rule_engine, "_do_search", fake_search)
    monkeypatch.setattr(
        rule_engine,
        "_do_load",
        lambda filename: {
            "accountMetrics.json": [
                {"listingId": "listing_10008", "skinCount": 100, "heroCount": 80, "valueScore": 90},
                {"listingId": "listing_10001", "skinCount": 120, "heroCount": 90, "valueScore": 88},
            ],
            "skinMaster.json": [{"skinId": "skin_1", "skinName": "杀手不太冷"}],
            "accountSkin.json": [
                {"listingId": "listing_10008", "skinId": "skin_1"},
                {"listingId": "listing_10001", "skinId": "skin_1"},
            ],
        }[filename],
    )
    history = [
        {"role": "user", "content": "我想买孙尚香带典藏皮肤的号"},
        {"role": "assistant", "content": "预算大概多少？你用 QQ 还是微信，安卓还是 iOS？"},
        {"role": "user", "content": "预算5000，安卓qq"},
    ]

    result = rule_engine.run_fallback("我想买孙尚香带典藏皮肤的号，预算3000，安卓qq", history)

    assert result["intake"]["slots"]["budget"]["max"] == 3000
    assert [item["price"] for item in result["recommendations"]] == [980]
    assert "4200" not in result["reply"]


def test_fallback_current_platform_correction_overrides_older_history_platform(monkeypatch):
    accounts = [_account("listing_qq"), _account("listing_wx")]
    accounts[0]["serverCode"] = "ANDROID_QQ"
    accounts[1]["serverCode"] = "ANDROID_WECHAT"

    def fake_search(**params):
        server_code = params.get("server_code")
        if server_code is None:
            return accounts
        return [account for account in accounts if account["serverCode"] == server_code]

    monkeypatch.setattr(rule_engine, "_do_search", fake_search)
    monkeypatch.setattr(
        rule_engine,
        "_do_load",
        lambda filename: {
            "accountMetrics.json": [
                {"listingId": "listing_qq", "skinCount": 100, "heroCount": 80, "valueScore": 90},
                {"listingId": "listing_wx", "skinCount": 120, "heroCount": 90, "valueScore": 88},
            ],
            "skinMaster.json": [{"skinId": "skin_1", "skinName": "杀手不太冷"}],
            "accountSkin.json": [
                {"listingId": "listing_qq", "skinId": "skin_1"},
                {"listingId": "listing_wx", "skinId": "skin_1"},
            ],
        }[filename],
    )
    history = [
        {"role": "user", "content": "我想要孙尚香带典藏皮肤的账号"},
        {"role": "assistant", "content": "预算大概多少？你用 QQ 还是微信，安卓还是 iOS？"},
        {"role": "user", "content": "预算5000，安卓qq"},
    ]

    result = rule_engine.run_fallback("说错了，是安卓微信区", history)

    assert result["intake"]["slots"]["platform"]["server_code"] == "ANDROID_WECHAT"
    assert [item["account_id"] for item in result["recommendations"]] == ["listing_wx"]
    assert "安卓微信区" in result["reply"]
    assert "安卓QQ区" not in result["reply"]
