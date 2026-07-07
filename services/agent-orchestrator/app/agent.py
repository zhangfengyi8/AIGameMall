"""
核心 Agent 模块。
集成 buyer-requirement-intake 和 account-recommendation-brief 两个技能。
支持规则解析前置 + LLM 生成推荐。
卡片数据通过独立搜索获取，确保前端始终能展示可点击的商品。
"""
import os
from pathlib import Path
from typing import AsyncIterator

import httpx
from openai import AsyncOpenAI
from agents import Agent, Runner, set_tracing_disabled
from agents.models.openai_responses import OpenAIResponsesModel

set_tracing_disabled(True)

from .instructions import INSTRUCTIONS
from .tools.search import search_accounts, _do_search
from .schemas.detail import format_card
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

guide_agent = Agent(
    name="游戏账号导购助手",
    instructions=INSTRUCTIONS,
    model=_model,
    tools=[search_accounts],
)


def _text_delta_from_stream_event(event) -> str:
    """从 Agents SDK 流式事件中提取文本增量。"""
    if getattr(event, "type", None) != "raw_response_event":
        return ""
    data = getattr(event, "data", None)
    if getattr(data, "type", None) != "response.output_text.delta":
        return ""
    return getattr(data, "delta", "") or ""


def _build_strategy_note(intake_result: dict, brief: dict, accounts: list[dict]) -> str:
    """构建注入 LLM 的推荐策略与候选账号摘要。"""
    account_summaries = []
    for acc in accounts[:10]:
        lid = acc.get("listingId", "?")
        price = acc.get("salePrice", 0)
        rank_name = acc.get("rankName", "?")
        rank_stars = acc.get("rankStars", 0)
        vip = acc.get("vipLevel", "?")
        real = acc.get("secondaryRealNameStatus", "")
        bind = acc.get("changeBindStatus", "")
        anti = acc.get("antiAddictionStatus", "")
        account_summaries.append(
            f"- {lid}: {price}元, {rank_name} {rank_stars}星, V{vip}, "
            f"防沉迷={anti}, 二次实名={real}, 换绑={bind}"
        )

    return (
        f"【需求解析结果】\n"
        f"意图: {intake_result['intent']}\n"
        f"必须条件: {'; '.join(intake_result['firm_requirements']) if intake_result['firm_requirements'] else '无'}\n"
        f"软偏好: {'; '.join(intake_result['soft_preferences']) if intake_result['soft_preferences'] else '无'}\n"
        f"排序权重: {brief['ranking']['weights']}\n\n"
        f"【候选账号列表】\n" + "\n".join(account_summaries) + "\n\n"
        f"请从以上候选账号中推荐最合适的 3 个，给出每个账号的推荐理由、性价比和风险说明。不要使用表格，用自然语言描述。"
    )


def _format_recommendation_cards(accounts: list[dict]) -> list[dict]:
    """将搜索结果去重并格式化为前端卡片。"""
    cards = []
    seen = set()
    for acc in accounts[:10]:
        aid = acc.get("listingId")
        if aid and aid not in seen:
            seen.add(aid)
            cards.append(format_card(acc))
            if len(cards) >= MAX_RECOMMENDATION_CARDS:
                break
    return cards


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
    intake_result = rule_intake(user_message)
    ready = intake_result["ready_for_recommendation"]

    # ========== 需求不明确，LLM 追问 ==========
    if not ready:
        clarifying = intake_result.get("clarifying_question", "")
        input_messages = (history or []) + [
            {"role": "system", "content": (
                "用户需求不够明确，不要搜索账号。先追问关键信息：优先问预算，其次问平台。"
                f"建议追问：{clarifying}"
            )},
            {"role": "user", "content": user_message},
        ]
        result = await Runner.run(guide_agent, input=input_messages)
        return {
            "reply": result.final_output,
            "recommendations": [],
            "history": result.to_input_list(),
            "intake": intake_result,
        }

    # ========== 需求明确：独立搜索 + LLM 推荐 ==========
    # 1. 用规则引擎搜到候选账号
    search_params = search_params_from_intake(intake_result)
    accounts = _do_search(**search_params)

    # 2. 构建推荐策略
    brief = build_query(intake_result)

    # 3. 将候选账号摘要注入 LLM，让 LLM 做推荐
    strategy_note = _build_strategy_note(intake_result, brief, accounts)

    input_messages = (history or []) + [
        {"role": "system", "content": strategy_note},
        {"role": "user", "content": user_message},
    ]
    result = await Runner.run(guide_agent, input=input_messages)

    # 4. 返回卡片数据（独立搜索，保证前端可展示）
    cards = _format_recommendation_cards(accounts)

    return {
        "reply": result.final_output,
        "recommendations": cards,
        "history": result.to_input_list(),
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
    intake_result = rule_intake(user_message)
    ready = intake_result["ready_for_recommendation"]

    if not ready:
        clarifying = intake_result.get("clarifying_question", "")
        input_messages = (history or []) + [
            {"role": "system", "content": (
                "用户需求不够明确，不要搜索账号。先追问关键信息：优先问预算，其次问平台。"
                f"建议追问：{clarifying}"
            )},
            {"role": "user", "content": user_message},
        ]
        stream_result = Runner.run_streamed(guide_agent, input=input_messages)
        full_text = ""
        async for event in stream_result.stream_events():
            delta = _text_delta_from_stream_event(event)
            if delta:
                full_text += delta
                yield {"event": "message_delta", "data": {"text": delta}}
        yield {
            "event": "done",
            "data": {
                "reply": full_text,
                "recommendations": [],
                "history": stream_result.to_input_list(),
                "intake": intake_result,
            },
        }
        return

    search_params = search_params_from_intake(intake_result)
    accounts = _do_search(**search_params)
    brief = build_query(intake_result)

    yield {
        "event": "strategy",
        "data": {
            "filters": brief["query"]["filters"],
            "weights": brief["ranking"]["weights"],
            "account_count": len(accounts),
            "account_ids": [acc.get("listingId", "") for acc in accounts[:10]],
        },
    }

    strategy_note = _build_strategy_note(intake_result, brief, accounts)
    input_messages = (history or []) + [
        {"role": "system", "content": strategy_note},
        {"role": "user", "content": user_message},
    ]
    stream_result = Runner.run_streamed(guide_agent, input=input_messages)

    full_text = ""
    async for event in stream_result.stream_events():
        delta = _text_delta_from_stream_event(event)
        if delta:
            full_text += delta
            yield {"event": "message_delta", "data": {"text": delta}}

    cards = _format_recommendation_cards(accounts)
    yield {"event": "recommendations", "data": cards}
    yield {
        "event": "done",
        "data": {
            "reply": full_text,
            "recommendations": cards,
            "history": stream_result.to_input_list(),
            "intake": intake_result,
        },
    }
