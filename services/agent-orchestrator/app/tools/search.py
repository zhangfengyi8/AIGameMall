"""
search_accounts Tool: 按条件从 JSON 关联表筛选账号并按价值评分排序。
"""
import json
import os
from pathlib import Path
from typing import Optional

from agents import function_tool

# 用 os.path 避免 __file__ 在中文路径下的问题
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
_DATA_DIR = os.path.join(_BASE, "data", "tags")


def _lj(fn: str) -> list[dict]:
    with open(os.path.join(_DATA_DIR, fn), encoding="utf-8-sig") as f:
        return json.load(f)


def _do_search(
    game_code: Optional[str] = None,
    server_code: Optional[str] = None,
    budget_min: Optional[int] = None,
    budget_max: Optional[int] = None,
    heroes: Optional[list[str]] = None,
    skins: Optional[list[str]] = None,
    keyword: Optional[str] = None,
    rank_name: Optional[str] = None,
    min_rank_stars: Optional[int] = None,
    min_vip_level: Optional[int] = None,
    min_skin_count: Optional[int] = None,
    min_hero_count: Optional[int] = None,
    min_collector_skin_count: Optional[int] = None,
    min_legend_skin_count: Optional[int] = None,
    min_limited_skin_count: Optional[int] = None,
    require_full_heroes: bool = False,
    anti_addiction: Optional[str] = None,
    secondary_real_name: Optional[str] = None,
    change_bind: Optional[str] = None,
    limit: int = 10,
) -> list[dict]:
    """search_accounts 的内部实现，供 fallback 和 tool 共用"""
    listings = _lj("accountListing.json")
    metrics_list = _lj("accountMetrics.json")
    hero_master = _lj("heroMaster.json")
    skin_master = _lj("skinMaster.json")
    acct_hero = _lj("accountHero.json")
    acct_skin = _lj("accountSkin.json")

    hero_name_to_id = {h["heroName"]: h["heroId"] for h in hero_master}
    skin_name_to_id = {s["skinName"]: s["skinId"] for s in skin_master}
    metrics_by_lid = {m["listingId"]: m for m in metrics_list}

    hero_ids_by_lid: dict[str, set] = {}
    for row in acct_hero:
        hero_ids_by_lid.setdefault(row["listingId"], set()).add(row["heroId"])
    skin_ids_by_lid: dict[str, set] = {}
    for row in acct_skin:
        skin_ids_by_lid.setdefault(row["listingId"], set()).add(row["skinId"])
    skin_by_id = {s["skinId"]: s for s in skin_master}

    rank_scores = {"青铜": 1, "白银": 2, "黄金": 3, "铂金": 5, "钻石": 7, "星耀": 10, "王者": 15, "无双王者": 18, "荣耀王者": 22}
    min_rank_score = rank_scores.get(rank_name, 0) if rank_name else 0

    result = []
    for lst in listings:
        lid = lst["listingId"]
        if game_code and lst.get("gameCode") != game_code:
            continue
        if server_code and lst.get("serverCode") != server_code:
            continue
        sp = lst.get("salePrice", 0)
        if budget_min is not None and sp < budget_min:
            continue
        if budget_max is not None and sp > budget_max:
            continue
        if rank_name and rank_scores.get(lst.get("rankName", ""), 0) < min_rank_score:
            continue
        if min_rank_stars is not None and lst.get("rankStars", 0) < min_rank_stars:
            continue
        if min_vip_level is not None and lst.get("vipLevel", 0) < min_vip_level:
            continue
        if anti_addiction and lst.get("antiAddictionStatus") != anti_addiction:
            continue
        if secondary_real_name and lst.get("secondaryRealNameStatus") != secondary_real_name:
            continue
        if change_bind and lst.get("changeBindStatus") != change_bind:
            continue
        metrics = metrics_by_lid.get(lid, {})
        if min_skin_count is not None and metrics.get("skinCount", 0) < min_skin_count:
            continue
        if min_hero_count is not None and metrics.get("heroCount", 0) < min_hero_count:
            continue
        if require_full_heroes and metrics.get("heroCount", 0) < len(hero_master):
            continue
        if min_collector_skin_count is not None or min_legend_skin_count is not None or min_limited_skin_count is not None:
            lid_skins = skin_ids_by_lid.get(lid, set())
            collector_count = 0
            legend_count = 0
            limited_count = 0
            for skin_id in lid_skins:
                skin = skin_by_id.get(skin_id, {})
                quality = skin.get("qualityCode")
                tags = skin.get("tagCodes", [])
                if quality == "COLLECTOR" or "典藏" in tags:
                    collector_count += 1
                if quality == "LEGEND" or "传说" in tags:
                    legend_count += 1
                if "限定" in tags:
                    limited_count += 1
            if min_collector_skin_count is not None and collector_count < min_collector_skin_count:
                continue
            if min_legend_skin_count is not None and legend_count < min_legend_skin_count:
                continue
            if min_limited_skin_count is not None and limited_count < min_limited_skin_count:
                continue
        if heroes:
            lid_heroes = hero_ids_by_lid.get(lid, set())
            if not any(hero_name_to_id.get(h) in lid_heroes for h in heroes if hero_name_to_id.get(h)):
                continue
        if skins:
            lid_skins = skin_ids_by_lid.get(lid, set())
            if not any(skin_name_to_id.get(s) in lid_skins for s in skins if skin_name_to_id.get(s)):
                continue
        if keyword:
            kw = keyword.lower()
            if kw not in lid.lower():
                lid_hero_ids = hero_ids_by_lid.get(lid, set())
                matched = any(kw in hm["heroName"].lower() for hm in hero_master if hm["heroId"] in lid_hero_ids)
                if not matched:
                    continue
        result.append(lst)

    result.sort(key=lambda a: -(metrics_by_lid.get(a["listingId"], {}).get("valueScore", 0) or 0))
    return result[:limit]


@function_tool
def search_accounts(
    game_code: Optional[str] = None,
    server_code: Optional[str] = None,
    budget_min: Optional[int] = None,
    budget_max: Optional[int] = None,
    heroes: Optional[list[str]] = None,
    skins: Optional[list[str]] = None,
    keyword: Optional[str] = None,
    rank_name: Optional[str] = None,
    min_rank_stars: Optional[int] = None,
    min_vip_level: Optional[int] = None,
    min_skin_count: Optional[int] = None,
    min_hero_count: Optional[int] = None,
    min_collector_skin_count: Optional[int] = None,
    min_legend_skin_count: Optional[int] = None,
    min_limited_skin_count: Optional[int] = None,
    require_full_heroes: bool = False,
    anti_addiction: Optional[str] = None,
    secondary_real_name: Optional[str] = None,
    change_bind: Optional[str] = None,
    limit: int = 10,
) -> list[dict]:
    """
    根据条件从 JSON 数据中筛选游戏账号，返回按价值评分排序的匹配账号列表。

    参数说明：
    - game_code: 游戏编码，"WZ"表示王者荣耀
    - server_code: 区服，如 "ANDROID_QQ"、"IOS_WECHAT"
    - budget_min: 最低预算（分，如 50000 表示 500 元）
    - budget_max: 最高预算（分）
    - heroes: 期望包含的英雄名称列表（如 ["李白", "孙尚香"]）
    - skins: 期望包含的皮肤名称列表（如 ["凤求凰"]）
    - keyword: 搜索关键词
    - rank_name: 最低段位要求（如 "星耀"、"王者"）
    - min_rank_stars: 最低王者星数
    - min_vip_level: 最低 VIP/贵族等级
    - min_skin_count: 最低皮肤数量
    - min_hero_count: 最低英雄数量
    - min_collector_skin_count: 最低典藏皮肤数量
    - min_legend_skin_count: 最低传说皮肤数量
    - min_limited_skin_count: 最低限定皮肤数量
    - require_full_heroes: 是否要求全英雄
    - anti_addiction: 防沉迷筛选，"NONE"或"RESTRICTED"
    - secondary_real_name: 二次实名筛选，"SUPPORTED"或"NOT_SUPPORTED"
    - change_bind: 换绑状态，"FULL_SUPPORTED"或"NOT_SUPPORTED"
    - limit: 最多返回数量（默认 10）
    """
    return _do_search(
        game_code=game_code,
        server_code=server_code,
        budget_min=budget_min,
        budget_max=budget_max,
        heroes=heroes,
        skins=skins,
        keyword=keyword,
        rank_name=rank_name,
        min_rank_stars=min_rank_stars,
        min_vip_level=min_vip_level,
        min_skin_count=min_skin_count,
        min_hero_count=min_hero_count,
        min_collector_skin_count=min_collector_skin_count,
        min_legend_skin_count=min_legend_skin_count,
        min_limited_skin_count=min_limited_skin_count,
        require_full_heroes=require_full_heroes,
        anti_addiction=anti_addiction,
        secondary_real_name=secondary_real_name,
        change_bind=change_bind,
        limit=limit,
    )
