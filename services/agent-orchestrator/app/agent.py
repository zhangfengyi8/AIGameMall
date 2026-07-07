import os
from pathlib import Path

import httpx
from openai import AsyncOpenAI
from agents import Agent, Runner, set_tracing_disabled
from agents.models.openai_responses import OpenAIResponsesModel

set_tracing_disabled(True)

from app.instructions import INSTRUCTIONS
from app.tools.search import search_accounts
from agents.items import ToolCallOutputItem
from app.schemas.detail import format_card

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

guide_agent = Agent(
    name="游戏账号导购助手",
    instructions=INSTRUCTIONS,
    model=_model,
    tools=[search_accounts],
)


async def run_agent(
    user_message: str,
    history: list | None = None,
) -> dict:
    """运行导购 Agent，返回推荐回复和相关卡片。"""
    input_messages = (history or []) + [{"role": "user", "content": user_message}]
    result = await Runner.run(guide_agent, input=input_messages)

    reply_text = result.final_output

    # 从 ToolCallOutputItem 中提取 search_accounts 的搜索结果
    search_results = []
    for item in result.new_items:
        if isinstance(item, ToolCallOutputItem):
            if isinstance(item.output, list) and len(item.output) > 0:
                if isinstance(item.output[0], dict) and "id" in item.output[0]:
                    search_results = item.output
                    break

    # 格式化为前端卡片（取前 10 个）
    cards = []
    if search_results:
        seen = set()
        for acc in search_results:
            aid = acc.get("id")
            if aid and aid not in seen:
                seen.add(aid)
                cards.append(format_card(acc))
                if len(cards) >= 10:
                    break

    return {
        "reply": reply_text,
        "recommendations": cards,
        "history": result.to_input_list(),
    }
