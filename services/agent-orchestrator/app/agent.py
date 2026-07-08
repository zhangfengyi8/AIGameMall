"""
核心 Agent 模块。
集成 buyer-requirement-intake 和 account-recommendation-brief 两个技能。
支持规则解析前置 + LLM 生成推荐。
卡片数据通过独立搜索获取，确保前端始终能展示可点击的商品。
"""
import os
import json
import re
from pathlib import Path
from typing import AsyncIterator

import httpx
from openai import AsyncOpenAI
from agents import Agent, Runner, set_tracing_disabled
from agents.models.openai_responses import OpenAIResponsesModel

set_tracing_disabled(True)

from .instructions import INSTRUCTIONS, RECOMMENDATION_INSTRUCTIONS

from .tools.search import search_accounts, _do_search
from .schemas.detail import format_card
from .skills.conversation_intent import classify_conversation_intent
from .skills.requirement_intake import intake as rule_intake, search_params_from_intake
from .skills.recommendation_brief import build_query

_env_path = Path(__file__).resolve().parent.parent / ".env"
if _env_path.exists():
    with open(str(_env_path), encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

API_KEY = os.environ.get("OPENAI_API_KEY", "")
BASE_URL = os.environ.get("OPENAI_BASE_URL", "http://127.0.0.1:15721/v1")
MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

_httpx_client = httpx.AsyncClient(proxy=None)
http_client = AsyncOpenAI(
    api_key=API_KEY,
    base_url=BASE_URL,
    http_client=_httpx_client,
)

_model = OpenAIResponsesModel(model=MODEL, openai_client=http_client)
MAX_RECOMMENDATION_CARDS = 3
# 候选池上限：需大于展示数量，供“换一批”排除已展示账号后仍有余量
CANDIDATE_POOL_LIMIT = 60
NO_MORE_ACCOUNTS_REPLY = "暂时没有其他符合要求的账号了呢~ 可以适当放宽预算、区服或皮肤要求，我再帮你找找。"
# 记录已展示账号 ID 的内部标记（存在 history 里跨轮传递，不展示给用户也不喂给 LLM）
_SHOWN_IDS_MARKER = "[[__shown_account_ids__]]"

guide_agent = Agent(
    name="游戏账号导购助手",
    instructions=INSTRUCTIONS,
    model=_model,
    tools=[search_accounts],
)

recommendation_agent = Agent(
    name="游戏账号导购助手",
    instructions=RECOMMENDATION_INSTRUCTIONS,
    model=_model,
    tools=[],
)

CHAT_INSTRUCTIONS = """你是王者荣耀游戏账号交易平台的 AI 导购助手，性格友好、轻松、有点亲和力。
用户现在在跟你闲聊，或者说了一句和买号不直接相关的话。请像真人一样自然、口语化地简短回应。

规则：
- 自然接住对方的话，可以适当幽默、有温度；不要每次都自我介绍，不要重复背诵你的功能列表。
- 回应对方之后，可以偶尔、轻描淡写地提一句“想找号随时跟我说”，但不要生硬推销，更不要每句都提。
- 如果对方问你是不是真人，坦诚说你是 AI 助手。
- 不协助任何违法违规请求（账号找回、盗号、绕过平台私下交易等），礼貌拒绝。
- 不承接与游戏账号导购无关的任务（写作业、写代码、算命、闲聊之外的杂活等），礼貌婉拒并说明你主要帮忙找王者荣耀账号。
- 回复必须是纯文本，简短（一般 1-3 句），不要用 Markdown、标题、列表或表情堆砌。"""

chat_agent = Agent(
    name="游戏账号导购助手",
    instructions=CHAT_INSTRUCTIONS,
    model=_model,
    tools=[],
)

# 这些意图交给 LLM 自然聊天；其余非商品意图（违规/拒买/身份/交易咨询）保持受控固定回复
_LLM_CHAT_INTENTS = {"general_chat", "unknown"}


def _text_delta_from_stream_event(event) -> str:
    """从 Agents SDK 流式事件中提取文本增量。"""
    if getattr(event, "type", None) != "raw_response_event":
        return ""
    data = getattr(event, "data", None)
    if getattr(data, "type", None) != "response.output_text.delta":
        return ""
    return getattr(data, "delta", "") or ""



_hero_skin_cache = None


def _load_skin_data():
    global _hero_skin_cache
    if _hero_skin_cache is not None:
        return
    _base = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "data", "tags")
    try:
        with open(os.path.join(_base, "skinMaster.json"), encoding="utf-8-sig") as f:
            sm = json.load(f)
        with open(os.path.join(_base, "accountSkin.json"), encoding="utf-8-sig") as f:
            ask = json.load(f)
        with open(os.path.join(_base, "heroMaster.json"), encoding="utf-8-sig") as f:
            hm = json.load(f)
        smap = {s["skinId"]: s for s in sm}
        lid_skins = {}
        for r in ask:
            lid_skins.setdefault(r["listingId"], []).append(r["skinId"])
        q_order = {"COLLECTION": 0, "LEGEND": 1}
        _hero_skin_cache = (smap, lid_skins, q_order)
    except Exception as _e:
        import traceback; traceback.print_exc()
        _hero_skin_cache = ({}, {}, {})


def _get_hero_skins_text(lid: str) -> str:
    smap, lid_skins, q_order = _hero_skin_cache or ({}, {}, {})
    sids = lid_skins.get(lid, [])
    ss = sorted(sids, key=lambda sid: q_order.get(smap.get(sid, {}).get("qualityCode", ""), 9))
    parts = []
    for sid in ss[:8]:
        s = smap.get(sid, {})
        if s:
            dcor = "[典藏]" if "荣耀典藏" in s.get("tagCodes", []) or s.get("qualityCode") == "COLLECTION" else ("[传说]" if s.get("qualityCode") == "LEGEND" else "")
            parts.append(s.get("heroName", "") + "·" + s.get("skinName", "") + dcor)
    return "、".join(parts) if parts else "暂无高价值皮肤数据"

def _build_strategy_note(intake_result: dict, brief: dict, accounts: list[dict]) -> str:
    """构建注入 LLM 的推荐策略与已选定账号摘要。
    accounts 已由规则层按价值评分排序，最多 3 个。
    LLM 只需要介绍这些账号，不需要再次选择。
    """
    account_summaries = []
    _load_skin_data()
    for acc in accounts:
        lid = acc.get("listingId", "")
        price = acc.get("salePrice", 0)
        rank_name = acc.get("rankName", "?")
        rank_stars = acc.get("rankStars", 0)
        vip = acc.get("vipLevel", "?")
        real = acc.get("secondaryRealNameStatus", "")
        bind = acc.get("changeBindStatus", "")
        anti = acc.get("antiAddictionStatus", "")
        risk_note = "无防沉迷" if anti == "NONE" else "有防沉迷限制"
        real_note = "支持二次实名" if real == "SUPPORTED" else "不支持二次实名"
        bind_note = "可换绑" if bind == "FULL_SUPPORTED" else "不可换绑"
        skin_text = _get_hero_skins_text(lid)
        account_summaries.append(
            f"【账号概况】价格{price}元, {rank_name}{rank_stars}星, V{vip}级, "
            f"皮肤/英雄: {skin_text}。"
        )

    return (
        f"【需求解析结果】\n"
        f"意图: {intake_result['intent']}\n"
        f"必须条件: {'; '.join(intake_result['firm_requirements']) if intake_result['firm_requirements'] else '无'}\n"
        f"软偏好: {'; '.join(intake_result['soft_preferences']) if intake_result['soft_preferences'] else '无'}\n"
        f"排序权重: {brief['ranking']['weights']}\n\n"
        f"【推荐账号列表】\n" + "\n".join(account_summaries) + "\n\n"
        f"以下账号已由系统按价值评分精选推荐，请用自然的买家导购语气介绍给用户。\n"
        f"回复总字数控制在 300 字以内。\n"
        f"每个账号用 1-2 句自然介绍即可，说明价格、段位、核心亮点和主要风险。\n"
        f"皮肤/英雄数据来自系统数据库，准确可靠。如果账号包含用户想要的皮肤，直接说出来，不需要让用户核实。\n"
        f"如果只有一个账号，开头写“找到一个比较匹配的账号，可以优先看看。”，然后写“推荐一：...”。\n"
        f"如果有多个账号，开头写“我筛到几款比较接近你需求的账号，可以按优先级看看：”，然后用“推荐一：...”“推荐二：...”“推荐三：...”分段。\n"
        f"每条推荐只讲差异化卖点，例如价格、段位/VIP、核心皮肤/资产；不要每条重复同一句性价比和风险套话。\n"
        f"交易风险和购买提醒只在所有推荐之后统一说一次。只有 1 个账号时，用“下单前注意事项：这款账号...”，不要说“这几款”；多个账号时，才可以说“这几款”。\n"
        f"不许向用户解释推荐数量规则，不许出现“整体描述”“数量不足”“不硬凑”“命中多少”“最多 3 个”“按规则筛选”等内部策略话术。\n"
        f"必须输出纯文本，不要使用 Markdown 标题、加粗、表格、代码块、引用块或分隔线。\n"
        f"不要写搜索过程，不要写长篇分析。\n"
        f"严禁暴露内部 ID 或字段名。绝对不能出现英文格式的内部编号和区服代号。\n"
        f"对用户只能使用推荐一、推荐二、推荐三、高段位款、性价比款、低风险款等展示名称。\n"
        f"如果没有推荐账号（列表为空），只用 1-2 句话说明没有匹配结果，并给 1 个放宽建议。"
    )


def _sanitize_public_reply(text: str) -> str:
    """清理自然语言回复中的内部 ID 和字段名，避免暴露给用户。"""
    replacements = {
        "listingId": "商品编号",
        "accountId": "账号编号",
        "serverCode": "区服",
        "gameCode": "游戏",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    text = re.sub(r"\blisting[_-]?\d*\b", "该账号", text, flags=re.IGNORECASE)
    text = re.sub(r"\bacc[_-]?\d*\b", "该账号", text, flags=re.IGNORECASE)
    # 替换内部区服代码为人类可读名称
    _SERVER_CODE_MAP = {
        "ANDROID_QQ": "安卓QQ",
        "ANDROID_WECHAT": "安卓微信",
        "IOS_QQ": "苹果QQ",
        "IOS_WECHAT": "苹果微信",
    }
    for _code, _name in _SERVER_CODE_MAP.items():
        text = text.replace(_code, _name)
    text = re.sub(r"(?m)^\s{0,3}#{1,6}\s*", "", text)
    text = re.sub(r"(?m)^\s*[-*_]{3,}\s*$", "", text)
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"__(.*?)__", r"\1", text)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"(?m)^\s*>\s?", "", text)
    text = re.sub(r"(?m)^\s*[-*+]\s+", "", text)
    return text.strip()


def _safe_stream_chunks(text: str, pending: str = "") -> tuple[str, str]:
    """对流式文本做轻量缓冲，避免内部 ID 分片漏出。"""
    combined = pending + text
    lower = combined.lower()
    risky_tokens = ("listing", "acc_", "acc-")
    risky_start = min([lower.find(token) for token in risky_tokens if lower.find(token) != -1] or [-1])
    if risky_start == -1:
        keep = min(len(combined), 8)
        if len(combined) <= keep:
            return "", combined
        safe_part = _sanitize_public_reply(combined[:-keep])
        pending_part = combined[-keep:]
        pending_part = _sanitize_public_reply(pending_part)
        return safe_part, pending_part

    safe_prefix = combined[:risky_start]
    risky_tail = combined[risky_start:]
    if re.search(r"\b(?:listing|acc)[_-]?\d+\b", risky_tail, flags=re.IGNORECASE):
        sanitized = _sanitize_public_reply(risky_tail)
        keep = min(len(sanitized), 12)
        output = safe_prefix + sanitized[:-keep]
        return output, sanitized[-keep:]
    return _sanitize_public_reply(safe_prefix), _sanitize_public_reply(risky_tail)


def _format_recommendation_cards(accounts: list[dict]) -> list[dict]:
    """将搜索结果去重并格式化为前端卡片。"""
    cards = []
    seen = set()
    for acc in accounts:
        aid = acc.get("listingId")
        if aid and aid not in seen:
            seen.add(aid)
            cards.append(format_card(acc))
            if len(cards) >= MAX_RECOMMENDATION_CARDS:
                break
    return cards


def _merged_user_message(user_message: str, history: list | None = None) -> str:
    """合并历史用户消息和当前消息，供规则解析补全多轮信息。"""
    user_parts: list[str] = [user_message.strip()]
    for item in history or []:
        if not isinstance(item, dict) or item.get("role") != "user":
            continue
        content = item.get("content", "")
        if isinstance(content, str) and content.strip():
            user_parts.append(content.strip())
    return "\n".join(user_parts)



def _extract_shown_ids(history: list | None) -> set[str]:
    """从 history 里的内部标记中解析出此前已展示过的账号 ID。"""
    shown: set[str] = set()
    for item in history or []:
        if not isinstance(item, dict):
            continue
        content = item.get("content", "")
        if isinstance(content, str) and content.startswith(_SHOWN_IDS_MARKER):
            payload = content[len(_SHOWN_IDS_MARKER):].strip()
            for token in payload.split(","):
                token = token.strip()
                if token:
                    shown.add(token)
    return shown


def _strip_markers(history: list | None) -> list:
    """移除内部标记消息，得到可安全喂给 LLM 的干净 history。"""
    cleaned = []
    for item in history or []:
        if isinstance(item, dict):
            content = item.get("content", "")
            if isinstance(content, str) and content.startswith(_SHOWN_IDS_MARKER):
                continue
        cleaned.append(item)
    return cleaned


def _with_shown_marker(history_list: list, shown_ids: set[str]) -> list:
    """在返回的 history 末尾写入已展示账号标记，供下一轮“换一批”排除。"""
    cleaned = _strip_markers(history_list)
    if shown_ids:
        cleaned = cleaned + [
            {"role": "system", "content": _SHOWN_IDS_MARKER + " " + ",".join(sorted(shown_ids))}
        ]
    return cleaned


def _conversational_history(history: list | None) -> list:
    """仅保留 user/assistant 对话消息，去掉系统注入的策略说明和内部标记，供闲聊 LLM 使用。"""
    convo = []
    for item in history or []:
        if not isinstance(item, dict):
            continue
        if item.get("role") not in ("user", "assistant"):
            continue
        content = item.get("content", "")
        if isinstance(content, str) and content.startswith(_SHOWN_IDS_MARKER):
            continue
        convo.append(item)
    return convo


def _controlled_chat_result(user_message: str, intent_result: dict, history: list | None = None) -> dict:
    reply = _sanitize_public_reply(intent_result.get("reply", ""))
    shown_ids = _extract_shown_ids(history)
    base_history = _strip_markers(history)
    new_history = base_history + [
        {"role": "user", "content": user_message},
        {"role": "assistant", "content": reply},
    ]
    return {
        "reply": reply,
        "recommendations": [],
        "history": _with_shown_marker(new_history, shown_ids),
        "intake": {
            "intent": intent_result.get("intent", "unknown"),
            "ready_for_recommendation": False,
            "controlled_chat": True,
        },
    }
async def run_agent(
    user_message: str,
    history: list | None = None,
) -> dict:
    """运行导购 Agent，返回推荐回复和相关卡片。

    流程：
    1. 规则引擎做 buyer-requirement-intake（需求理解）
    2. 如果需求明确 → 搜账号 + 构建推荐策略注入 LLM
    3. 如果需求模糊 → 让 LLM 自行追问
    4. 独立搜索拿到完整卡片数据返回前端
    """
    intent_result = classify_conversation_intent(user_message, history)
    if not intent_result["should_search"]:
        if intent_result.get("intent") in _LLM_CHAT_INTENTS:
            shown_ids = _extract_shown_ids(history)
            convo = _conversational_history(history)
            result = await Runner.run(chat_agent, input=convo + [{"role": "user", "content": user_message}])
            reply = _sanitize_public_reply(result.final_output)
            new_history = convo + [
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": reply},
            ]
            return {
                "reply": reply,
                "recommendations": [],
                "history": _with_shown_marker(new_history, shown_ids),
                "intake": {
                    "intent": intent_result.get("intent", "unknown"),
                    "ready_for_recommendation": False,
                    "controlled_chat": True,
                },
            }
        return _controlled_chat_result(user_message, intent_result, history)

    is_next_batch = bool(intent_result.get("next_batch"))
    shown_ids = _extract_shown_ids(history)
    base_history = _strip_markers(history)

    intake_result = rule_intake(_merged_user_message(user_message, history))
    ready = intake_result["ready_for_recommendation"]

    # ========== 需求不明确，LLM 追问 ==========
    if not ready:
        clarifying = intake_result.get("clarifying_question", "")
        input_messages = base_history + [
            {"role": "system", "content": (
                "用户需求不够明确，不要搜索账号。只追问 missing_required_slots 或 clarifying_question 指向的缺失信息。"
                "如果需求解析结果里已经有平台、预算、VIP、段位、英雄或皮肤，禁止重复追问这些已知信息。"
                f"已解析平台：{intake_result['slots'].get('platform')}；已解析预算：{intake_result['slots'].get('budget')}。"
                f"建议追问：{clarifying}"
            )},
            {"role": "user", "content": user_message},
        ]
        result = await Runner.run(guide_agent, input=input_messages)
        return {
            "reply": _sanitize_public_reply(result.final_output),
            "recommendations": [],
            "history": _with_shown_marker(result.to_input_list(), shown_ids),
            "intake": intake_result,
        }

    # ========== 需求明确：独立搜索 + LLM 推荐 ==========
    # 1. 用规则引擎搜到候选账号（放大候选池，供“换一批”排除已展示账号后仍有余量）
    search_params = search_params_from_intake(intake_result)
    search_params.setdefault("limit", CANDIDATE_POOL_LIMIT)
    accounts = _do_search(**search_params)

    # 2. “换一批”时排除已展示账号；普通推荐则重置已展示集合
    if is_next_batch:
        candidates = [a for a in accounts if a.get("listingId") not in shown_ids]
    else:
        candidates = accounts
    selected_accounts = candidates[:MAX_RECOMMENDATION_CARDS]

    # 3. “换一批”没有更多结果 → 明确告知，保留已展示标记
    if is_next_batch and not selected_accounts:
        new_history = base_history + [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": NO_MORE_ACCOUNTS_REPLY},
        ]
        return {
            "reply": NO_MORE_ACCOUNTS_REPLY,
            "recommendations": [],
            "history": _with_shown_marker(new_history, shown_ids),
            "intake": intake_result,
        }

    selected_ids = {a.get("listingId") for a in selected_accounts if a.get("listingId")}
    new_shown = (shown_ids | selected_ids) if is_next_batch else set(selected_ids)

    # 4. 构建推荐策略
    brief = build_query(intake_result)

    # 5. 将推荐账号摘要注入 LLM，LLM 只负责介绍，不再选择
    strategy_note = _build_strategy_note(intake_result, brief, selected_accounts)

    input_messages = base_history + [
        {"role": "system", "content": strategy_note},
        {"role": "user", "content": user_message},
    ]
    result = await Runner.run(recommendation_agent, input=input_messages)

    # 6. 返回卡片数据（与 LLM 看到的一致，保证同源）
    cards = _format_recommendation_cards(selected_accounts)

    return {
        "reply": _sanitize_public_reply(result.final_output),
        "recommendations": cards,
        "history": _with_shown_marker(result.to_input_list(), new_shown),
        "intake": intake_result,
    }


async def run_agent_stream(
    user_message: str,
    history: list | None = None,
) -> AsyncIterator[dict]:
    """流式运行导购 Agent。

    事件格式：
    - {"event": "strategy", "data": {...}}
    - {"event": "message_delta", "data": {"text": "..."}}
    - {"event": "recommendations", "data": [/* cards */]}
    - {"event": "done", "data": {"reply", "history", "intake"}}
    """
    intent_result = classify_conversation_intent(user_message, history)
    if not intent_result["should_search"]:
        if intent_result.get("intent") in _LLM_CHAT_INTENTS:
            shown_ids = _extract_shown_ids(history)
            convo = _conversational_history(history)
            stream_result = Runner.run_streamed(
                chat_agent, input=convo + [{"role": "user", "content": user_message}]
            )
            full_text = ""
            pending_text = ""
            async for event in stream_result.stream_events():
                delta = _text_delta_from_stream_event(event)
                if delta:
                    full_text += delta
                    safe_delta, pending_text = _safe_stream_chunks(delta, pending_text)
                    if safe_delta:
                        yield {"event": "message_delta", "data": {"text": safe_delta}}
            if pending_text:
                yield {"event": "message_delta", "data": {"text": _sanitize_public_reply(pending_text)}}
            full_text = _sanitize_public_reply(full_text)
            new_history = convo + [
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": full_text},
            ]
            yield {"event": "recommendations", "data": []}
            yield {
                "event": "done",
                "data": {
                    "reply": full_text,
                    "recommendations": [],
                    "history": _with_shown_marker(new_history, shown_ids),
                    "intake": {
                        "intent": intent_result.get("intent", "unknown"),
                        "ready_for_recommendation": False,
                        "controlled_chat": True,
                    },
                },
            }
            return
        result = _controlled_chat_result(user_message, intent_result, history)
        yield {"event": "message_delta", "data": {"text": result["reply"]}}
        yield {"event": "recommendations", "data": []}
        yield {"event": "done", "data": result}
        return

    is_next_batch = bool(intent_result.get("next_batch"))
    shown_ids = _extract_shown_ids(history)
    base_history = _strip_markers(history)

    intake_result = rule_intake(_merged_user_message(user_message, history))
    ready = intake_result["ready_for_recommendation"]

    if not ready:
        clarifying = intake_result.get("clarifying_question", "")
        input_messages = base_history + [
            {"role": "system", "content": (
                "用户需求不够明确，不要搜索账号。只追问 missing_required_slots 或 clarifying_question 指向的缺失信息。"
                "如果需求解析结果里已经有平台、预算、VIP、段位、英雄或皮肤，禁止重复追问这些已知信息。"
                f"已解析平台：{intake_result['slots'].get('platform')}；已解析预算：{intake_result['slots'].get('budget')}。"
                f"建议追问：{clarifying}"
            )},
            {"role": "user", "content": user_message},
        ]
        stream_result = Runner.run_streamed(guide_agent, input=input_messages)
        full_text = ""
        pending_text = ""
        async for event in stream_result.stream_events():
            delta = _text_delta_from_stream_event(event)
            if delta:
                full_text += delta
                safe_delta, pending_text = _safe_stream_chunks(delta, pending_text)
                if safe_delta:
                    yield {"event": "message_delta", "data": {"text": safe_delta}}
        if pending_text:
            yield {"event": "message_delta", "data": {"text": _sanitize_public_reply(pending_text)}}
        full_text = _sanitize_public_reply(full_text)
        yield {
            "event": "done",
            "data": {
                "reply": full_text,
                "recommendations": [],
                "history": _with_shown_marker(stream_result.to_input_list(), shown_ids),
                "intake": intake_result,
            },
        }
        return

    search_params = search_params_from_intake(intake_result)
    search_params.setdefault("limit", CANDIDATE_POOL_LIMIT)
    accounts = _do_search(**search_params)

    if is_next_batch:
        candidates = [a for a in accounts if a.get("listingId") not in shown_ids]
    else:
        candidates = accounts
    selected_accounts = candidates[:MAX_RECOMMENDATION_CARDS]

    # “换一批”没有更多结果 → 明确告知，保留已展示标记
    if is_next_batch and not selected_accounts:
        new_history = base_history + [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": NO_MORE_ACCOUNTS_REPLY},
        ]
        yield {"event": "message_delta", "data": {"text": NO_MORE_ACCOUNTS_REPLY}}
        yield {"event": "recommendations", "data": []}
        yield {
            "event": "done",
            "data": {
                "reply": NO_MORE_ACCOUNTS_REPLY,
                "recommendations": [],
                "history": _with_shown_marker(new_history, shown_ids),
                "intake": intake_result,
            },
        }
        return

    selected_ids = {a.get("listingId") for a in selected_accounts if a.get("listingId")}
    new_shown = (shown_ids | selected_ids) if is_next_batch else set(selected_ids)

    brief = build_query(intake_result)

    yield {
        "event": "strategy",
        "data": {
            "filters": brief["query"]["filters"],
            "weights": brief["ranking"]["weights"],
            "account_count": len(candidates),
            "account_ids": [acc.get("listingId", "") for acc in selected_accounts],
        },
    }

    strategy_note = _build_strategy_note(intake_result, brief, selected_accounts)
    input_messages = base_history + [
        {"role": "system", "content": strategy_note},
        {"role": "user", "content": user_message},
    ]
    stream_result = Runner.run_streamed(recommendation_agent, input=input_messages)

    full_text = ""
    pending_text = ""
    async for event in stream_result.stream_events():
        delta = _text_delta_from_stream_event(event)
        if delta:
            full_text += delta
            safe_delta, pending_text = _safe_stream_chunks(delta, pending_text)
            if safe_delta:
                yield {"event": "message_delta", "data": {"text": safe_delta}}
    if pending_text:
        yield {"event": "message_delta", "data": {"text": _sanitize_public_reply(pending_text)}}

    full_text = _sanitize_public_reply(full_text)
    cards = _format_recommendation_cards(selected_accounts)
    yield {"event": "recommendations", "data": cards}
    yield {
        "event": "done",
        "data": {
            "reply": full_text,
            "recommendations": cards,
            "history": _with_shown_marker(stream_result.to_input_list(), new_shown),
            "intake": intake_result,
        },
    }
