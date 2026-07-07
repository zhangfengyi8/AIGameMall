import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.skills.conversation_intent import classify_conversation_intent


def test_identity_question_returns_controlled_assistant_reply():
    result = classify_conversation_intent("你是谁", [])

    assert result["intent"] == "assistant_identity"
    assert result["should_search"] is False
    assert "智能导购助手" in result["reply"]
    assert "预算" in result["reply"]


def test_product_request_enters_recommendation_flow():
    result = classify_conversation_intent("帮我找带孙尚香荣耀典藏皮肤的账号", [])

    assert result["intent"] == "buy_account"
    assert result["should_search"] is True
    assert result["reply"] == ""


def test_contextual_numeric_followup_can_update_budget():
    history = [
        {"role": "user", "content": "帮我找带孙尚香荣耀典藏皮肤的账号"},
        {"role": "assistant", "content": "预算大概多少？你用 QQ 还是微信，安卓还是 iOS？"},
    ]

    result = classify_conversation_intent("8000预算，安卓qq区", history)

    assert result["intent"] == "clarify_followup"
    assert result["should_search"] is True


def test_standalone_numeric_input_without_active_buying_context_does_not_repeat_recommendations():
    result = classify_conversation_intent("6666", [])

    assert result["intent"] == "unknown"
    assert result["should_search"] is False
    assert "没太理解" in result["reply"]


def test_not_buying_is_respected_without_sales_push():
    result = classify_conversation_intent("不买了，随便聊聊", [])

    assert result["intent"] == "not_buying"
    assert result["should_search"] is False
    assert "没问题" in result["reply"]
    assert "下单" not in result["reply"]
    assert "推荐账号" not in result["reply"]


def test_general_chat_gets_controlled_short_reply():
    result = classify_conversation_intent("今天心情不错", [])

    assert result["intent"] == "general_chat"
    assert result["should_search"] is False
    assert "挺好" in result["reply"] or "不错" in result["reply"]


def test_unsafe_private_trade_request_is_refused():
    result = classify_conversation_intent("教我怎么绕过平台私下交易避免风控", [])

    assert result["intent"] == "unsafe"
    assert result["should_search"] is False
    assert "不能" in result["reply"]
    assert "平台" in result["reply"]


def test_numeric_after_completed_recommendation_does_not_reuse_old_filters():
    history = [
        {"role": "user", "content": "预算5000，安卓qq"},
        {"role": "assistant", "content": "我筛到几款比较接近你需求的账号，可以按优先级看看：\n推荐一：...\n推荐二：..."},
    ]

    result = classify_conversation_intent("6666", history)

    assert result["intent"] == "unknown"
    assert result["should_search"] is False


def test_trade_safety_question_after_recommendation_returns_advice_without_cards():
    history = [
        {"role": "user", "content": "预算5000，安卓qq"},
        {"role": "assistant", "content": "我筛到几款比较接近你需求的账号，可以按优先级看看：\n推荐一：...\n推荐二：..."},
    ]

    result = classify_conversation_intent("账号交易安全吗", history)

    assert result["intent"] == "trade_advice"
    assert result["should_search"] is False
    assert "实名" in result["reply"]
    assert "换绑" in result["reply"]
