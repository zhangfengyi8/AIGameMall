"""受控对话意图分流。

在进入账号需求解析和搜索之前，先识别非商品对话，避免闲聊、身份问题、
拒绝购买或无意义输入复用历史导购结果。
"""
from __future__ import annotations

import re
from typing import Any

BUYING_KEYWORDS = (
    "账号",
    "号",
    "皮肤",
    "英雄",
    "段位",
    "王者",
    "荣耀典藏",
    "贵族",
    "v8",
    "v10",
    "预算",
    "安卓",
    "苹果",
    "ios",
    "qq",
    "微信",
    "找",
    "买",
    "推荐",
    "筛",
)

FOLLOWUP_KEYWORDS = (
    "预算",
    "安卓",
    "苹果",
    "ios",
    "qq",
    "微信",
    "区",
    "以内",
    "以下",
    "以上",
    "左右",
    "可加",
    "不要",
    "要",
    "带",
)

IDENTITY_PATTERNS = (
    "你是谁",
    "你是啥",
    "你是什么",
    "你能干嘛",
    "你会什么",
    "介绍一下你",
)

NOT_BUYING_PATTERNS = (
    "不买了",
    "先不买",
    "暂时不买",
    "我不买",
    "不想买",
    "不用推荐",
    "别推荐",
    "随便聊聊",
)

UNSAFE_PATTERNS = (
    "私下交易",
    "绕过平台",
    "规避风控",
    "绕风控",
    "防找回教程",
    "找回账号",
    "破解",
    "盗号",
    "骗",
    "洗号",
)

GENERAL_CHAT_PATTERNS = (
    "你好",
    "hello",
    "hi",
    "心情",
    "无聊",
    "聊聊",
    "哈哈",
    "谢谢",
    "天气",
    "好的",
    "好吧",
    "行",
    "可以",
    "嗯",
    "嗯嗯",
    "哦",
    "知道了",
    "了解",
    "明白",
    "懂了",
    "不错",
    "厉害",
    "牛",
    "666",
    "再见",
    "拜拜",
    "bye",
    "晚安",
    "早安",
    "对",
    "是的",
    "没错",
    "还好",
    "一般",
    "ok",
    "好嘞",
    "收到",
    "感谢",
    "辛苦了",
    "随便看看",
)

TRADE_ADVICE_PATTERNS = (
    "交易安全",
    "安全吗",
    "安全不",
    "实名",
    "换绑",
    "防沉迷",
    "找回风险",
    "会不会找回",
    "交易注意",
    "注意事项",
)

COMPLETED_RECOMMENDATION_PATTERNS = (
    "我筛到",
    "找到一个比较匹配",
    "推荐一",
    "下单前注意事项",
    "交易安全上",
)

NEXT_BATCH_PATTERNS = (
    "换一批",
    "换一个",
    "换个",
    "换其他",
    "换别的",
    "换换",
    "换一换",
    "再换",
    "还有别的",
    "还有其他",
    "还有没有",
    "还有吗",
    "还有更多",
    "有没有其他",
    "有没有别的",
    "有没有更多",
    "没有其他",
    "没有别的",
    "其他的呢",
    "别的呢",
    "别的号",
    "其他号",
    "看看别的",
    "看看其他",
    "再来几个",
    "再来一批",
    "再看看别",
    "更多推荐",
    "不满意",
    "不喜欢这",
    "这几个不行",
    "这些不行",
    "都不行",
    "都不喜欢",
)

IDENTITY_REPLY = "我是你的游戏账号智能导购助手，可以按预算、区服、英雄皮肤、段位和风险偏好帮你筛选账号。"
NOT_BUYING_REPLY = "没问题，先不看账号也可以。你想了解账号交易注意事项、王者皮肤配置，或者随便聊聊都行。"
UNSAFE_REPLY = "这个我不能协助。账号交易建议走平台担保流程，重点确认实名、换绑、防沉迷和售后规则，避免私下交易风险。"
TRADE_ADVICE_REPLY = "账号交易要重点看平台担保、实名是否可改、是否支持换绑、防沉迷状态和售后规则；不要私下交易，也不要相信绝对安全承诺。"
GENERAL_CHAT_REPLY = "好的，有什么需要随时说。想找账号的话，告诉我预算和区服就行。"
UNKNOWN_REPLY = "我是游戏账号导购助手，主要帮你找王者荣耀账号。你可以告诉我预算、区服（QQ/微信、安卓/苹果）和想要的英雄皮肤，我来帮你筛选。"


def classify_conversation_intent(user_message: str, history: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """识别当前消息是否应该进入商品推荐流程。"""
    text = (user_message or "").strip()
    normalized = text.lower()

    if not text:
        return _result("unknown", UNKNOWN_REPLY, False)

    if _contains_any(normalized, UNSAFE_PATTERNS):
        return _result("unsafe", UNSAFE_REPLY, False)

    if _contains_any(normalized, NOT_BUYING_PATTERNS):
        return _result("not_buying", NOT_BUYING_REPLY, False)

    if _contains_any(normalized, IDENTITY_PATTERNS):
        return _result("assistant_identity", IDENTITY_REPLY, False)

    if _contains_any(normalized, TRADE_ADVICE_PATTERNS):
        return _result("trade_advice", TRADE_ADVICE_REPLY, False)

    if _contains_any(normalized, NEXT_BATCH_PATTERNS) and _has_active_buying_context(history):
        return {"intent": "next_batch", "reply": "", "should_search": True, "next_batch": True}

    if _is_buying_message(normalized):
        if _is_followup_message(normalized) and _has_active_buying_context(history):
            return _result("clarify_followup", "", True)
        return _result("buy_account", "", True)

    if _is_numeric_only(normalized):
        if _is_waiting_for_clarification(history):
            return _result("clarify_followup", "", True)
        if _contains_any(normalized, GENERAL_CHAT_PATTERNS):
            return _result("general_chat", GENERAL_CHAT_REPLY, False)
        return _result("unknown", UNKNOWN_REPLY, False)

    if _contains_any(normalized, GENERAL_CHAT_PATTERNS):
        return _result("general_chat", GENERAL_CHAT_REPLY, False)

    return _result("unknown", UNKNOWN_REPLY, False)


def _result(intent: str, reply: str, should_search: bool) -> dict[str, Any]:
    return {"intent": intent, "reply": reply, "should_search": should_search}


def _contains_any(text: str, patterns: tuple[str, ...]) -> bool:
    return any(pattern in text for pattern in patterns)


def _is_numeric_only(text: str) -> bool:
    return bool(re.fullmatch(r"\d+(?:\.\d+)?", text))


def _is_followup_message(text: str) -> bool:
    return _is_numeric_only(text) or _contains_any(text, FOLLOWUP_KEYWORDS)


def _is_buying_message(text: str) -> bool:
    if _contains_any(text, BUYING_KEYWORDS):
        return True
    return bool(re.search(r"\d+\s*(预算|以内|以下|以上|左右)", text))


def _is_waiting_for_clarification(history: list[dict[str, Any]] | None) -> bool:
    for item in reversed(history or []):
        if not isinstance(item, dict):
            continue
        content = item.get("content", "")
        if not isinstance(content, str):
            continue
        text = content.strip().lower()
        if not text:
            continue
        if _contains_any(text, COMPLETED_RECOMMENDATION_PATTERNS):
            return False
        if _contains_any(text, ("预算大概多少", "qq 还是微信", "qq还是微信", "安卓还是 ios", "安卓还是ios")):
            return True
    return False


def _has_active_buying_context(history: list[dict[str, Any]] | None) -> bool:
    for item in reversed(history or []):
        if not isinstance(item, dict):
            continue
        content = item.get("content", "")
        if not isinstance(content, str):
            continue
        text = content.strip().lower()
        if not text:
            continue
        if _contains_any(text, NOT_BUYING_PATTERNS):
            return False
        if _contains_any(text, ("预算大概多少", "qq 还是微信", "qq还是微信", "安卓还是 ios", "安卓还是ios")):
            return True
        if _is_buying_message(text):
            return True
    return False
