"""
查询账号详情 + 卡片格式化（适配新数据结构）。
优先使用关联表（metrics/hero/skin）丰富卡片信息。
"""
import json
import os

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
_DATA_DIR = os.path.join(_BASE, "data", "tags")


def _load_json(filename: str) -> list[dict]:
    with open(os.path.join(_DATA_DIR, filename), encoding="utf-8-sig") as f:
        return json.load(f)


# 缓存关联表，避免重复 IO
_metrics_by_lid: dict[str, dict] | None = None
_hero_master: list[dict] | None = None
_skin_master: list[dict] | None = None


def _ensure_cache():
    global _metrics_by_lid, _hero_master, _skin_master
    if _metrics_by_lid is None:
        metrics_list = _load_json("accountMetrics.json")
        _metrics_by_lid = {m["listingId"]: m for m in metrics_list}
        _hero_master = _load_json("heroMaster.json")
        _skin_master = _load_json("skinMaster.json")


def get_listings_by_ids(ids: list[str]) -> list[dict]:
    """根据 listingId 列表查询账号"""
    all_listings = _load_json("accountListing.json")
    id_set = set(ids)
    found = [lst for lst in all_listings if lst["listingId"] in id_set]
    id_order = {aid: i for i, aid in enumerate(ids)}
    found.sort(key=lambda a: id_order.get(a["listingId"], 999))
    return found


def format_card(listing: dict) -> dict:
    """将账号数据格式化为前端推荐卡片（完整字段）。"""
    _ensure_cache()
    lid = listing["listingId"]
    metrics = _metrics_by_lid.get(lid, {}) if _metrics_by_lid else {}

    # 找账号名下的英雄和皮肤
    hero_names = []
    skin_names = []
    if _hero_master and _skin_master:
        acct_hero = _load_json("accountHero.json")
        acct_skin = _load_json("accountSkin.json")
        hero_id_to_name = {h["heroId"]: h["heroName"] for h in _hero_master}
        skin_id_to_name = {s["skinId"]: s["skinName"] for s in _skin_master}
        for row in acct_hero:
            if row["listingId"] == lid and row["heroId"] in hero_id_to_name:
                hero_names.append(hero_id_to_name[row["heroId"]])
        for row in acct_skin:
            if row["listingId"] == lid and row["skinId"] in skin_id_to_name:
                skin_names.append(skin_id_to_name[row["skinId"]])

    return {
        "account_id": lid,
        "accountId": listing.get("accountId", ""),
        "game_code": listing.get("gameCode", ""),
        "server_code": listing.get("serverCode", ""),
        "price": listing.get("salePrice", 0),
        "vip_level": listing.get("vipLevel"),
        "rank_name": listing.get("rankName", ""),
        "rank_stars": listing.get("rankStars", 0),
        "anti_addiction": listing.get("antiAddictionStatus", ""),
        "secondary_real_name": listing.get("secondaryRealNameStatus", ""),
        "change_bind": listing.get("changeBindStatus", ""),
        "skin_count": metrics.get("skinCount", 0) if metrics else 0,
        "hero_count": metrics.get("heroCount", 0) if metrics else 0,
        "value_score": metrics.get("valueScore", 0) if metrics else 0,
        "heroes": hero_names,
        "skins": skin_names,
    }