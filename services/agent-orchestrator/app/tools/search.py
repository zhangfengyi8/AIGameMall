"""
search_accounts Tool: 按条件从 JSON 筛选账号并按性价比排序。
"""
import json
import os
from pathlib import Path
from typing import Optional

from agents import function_tool

# 性价比排序权重
_VALUE_ORDER = {"excellent": 0, "good": 1, "fair": 2, "expensive": 3}

# 段位权重缓存
_RANK_SCORE_MAP = {}


def _load_rank_map() -> dict[str, int]:
    """加载段位权重映射"""
    rank_path = Path(__file__).resolve().parent.parent.parent.parent.parent / "data" / "tags" / "ranks.json"
    try:
        with open(rank_path, encoding="utf-8-sig") as f:
            ranks = json.load(f)
        return {r["name"]: r["rank_score"] for r in ranks}
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        return {}


def _load_accounts() -> list[dict]:
    """加载账号 JSON 数据"""
    accounts_path = Path(__file__).resolve().parent.parent.parent.parent.parent / "data" / "accounts" / "accounts.json"
    with open(accounts_path, encoding="utf-8-sig") as f:
        return json.load(f)


def _extract_rank_score(rank_text: str) -> int | None:
    """从段位文本中提取 rank_score"""
    global _RANK_SCORE_MAP
    if not _RANK_SCORE_MAP:
        _RANK_SCORE_MAP = _load_rank_map()
    if not _RANK_SCORE_MAP:
        return None
    for rank_name, score in _RANK_SCORE_MAP.items():
        if rank_name in rank_text:
            return score
    return None


def _do_search(
    game_id: Optional[str] = None,
    budget_min: Optional[float] = None,
    budget_max: Optional[float] = None,
    rank_min: Optional[int] = None,
    heroes: Optional[list[str]] = None,
    skins: Optional[list[str]] = None,
    tags: Optional[list[str]] = None,
    keyword: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 10,
) -> list[dict]:
    """search_accounts 的内部实现（纯函数，供 fallback 和 tool 共用）"""
    accounts = _load_accounts()
    result = []

    for acc in accounts:
        if acc.get("status") != "on_sale":
            continue
        if game_id and acc.get("game", {}).get("id") != game_id:
            continue
        if category and acc.get("category") != category:
            continue

        price = acc.get("price", 0)
        if budget_min is not None and price < budget_min:
            continue
        if budget_max is not None and price > budget_max:
            continue

        if rank_min is not None:
            rank_text = acc.get("rank", {}).get("current", "")
            rs = _extract_rank_score(rank_text)
            if rs is None or rs < rank_min:
                continue

        if heroes:
            acc_heroes = [h.lower() for h in acc.get("highlights", {}).get("heroes", [])]
            if not any(h.lower() in acc_heroes for h in heroes):
                continue

        if skins:
            acc_skins = [s.lower() for s in acc.get("highlights", {}).get("skins", [])]
            if not any(s.lower() in acc_skins for s in skins):
                continue

        if tags:
            acc_tags = [t.lower() for t in acc.get("highlights", {}).get("tags", [])]
            if not any(t.lower() in acc_tags for t in tags):
                continue

        if keyword:
            kw = keyword.lower()
            title = acc.get("title", "").lower()
            acc_tags_text = " ".join(acc.get("highlights", {}).get("tags", [])).lower()
            if kw not in title and kw not in acc_tags_text:
                continue

        result.append(acc)

    result.sort(
        key=lambda a: (
            _VALUE_ORDER.get(a.get("valuation", {}).get("value_level", "fair"), 99),
            a.get("price", 0),
        )
    )

    return result[:limit]


@function_tool
def search_accounts(
    game_id: Optional[str] = None,
    budget_min: Optional[float] = None,
    budget_max: Optional[float] = None,
    rank_min: Optional[int] = None,
    heroes: Optional[list[str]] = None,
    skins: Optional[list[str]] = None,
    tags: Optional[list[str]] = None,
    keyword: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 10,
) -> list[dict]:
    """
    根据条件从 JSON 数据中筛选游戏账号，返回按性价比排序的匹配账号列表。

    参数说明：
    - game_id: 游戏 ID，如 "honor_of_kings"
    - budget_min: 最低预算
    - budget_max: 最高预算
    - rank_min: 最低段位分数（rank_score）
    - heroes: 期望包含的英雄列表
    - skins: 期望包含的皮肤列表
    - tags: 期望包含的标签列表
    - keyword: 搜索关键词（匹配标题和亮点标签）
    - category: 账号分类，如"皮肤号"、"技术号"、"低价号"
    - limit: 最多返回数量（默认 10）
    """
    return _do_search(
        game_id=game_id,
        budget_min=budget_min,
        budget_max=budget_max,
        rank_min=rank_min,
        heroes=heroes,
        skins=skins,
        tags=tags,
        keyword=keyword,
        category=category,
        limit=limit,
    )
