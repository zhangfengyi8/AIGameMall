import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.schemas.accounts import AccountAssets, AccountDetail, AccountRisk


SERVER_LABELS = {
    "ANDROID_QQ": "安卓QQ",
    "ANDROID_WECHAT": "安卓微信",
    "IOS_QQ": "苹果QQ",
    "IOS_WECHAT": "苹果微信",
}

PLATFORM_LABELS = {
    "ANDROID_QQ": "QQ",
    "IOS_QQ": "QQ",
    "ANDROID_WECHAT": "微信",
    "IOS_WECHAT": "微信",
}

ANTI_ADDICTION_LABELS = {
    "NONE": "无防沉迷",
    "RESTRICTED": "有防沉迷限制",
}

SECONDARY_REAL_NAME_LABELS = {
    "SUPPORTED": "支持二次实名",
    "NOT_SUPPORTED": "不支持二次实名",
}

CHANGE_BIND_LABELS = {
    "FULL_SUPPORTED": "支持换绑",
    "NOT_SUPPORTED": "不支持换绑",
}


@lru_cache(maxsize=1)
def load_tag_rows(filename: str) -> tuple[dict[str, Any], ...]:
    data_path = _repo_root() / "data" / "tags" / filename
    with data_path.open("r", encoding="utf-8-sig") as data_file:
        payload = json.load(data_file)

    if not isinstance(payload, list):
        return ()

    return tuple(account for account in payload if isinstance(account, dict))


@lru_cache(maxsize=1)
def load_listing_rows() -> tuple[dict[str, Any], ...]:
    return load_tag_rows("accountListing.json")


def get_account_detail(account_id: str) -> AccountDetail | None:
    for listing in load_listing_rows():
        if listing.get("listingId") == account_id or listing.get("accountId") == account_id:
            return _to_account_detail(listing=listing)

    return None


def _to_account_detail(*, listing: dict[str, Any]) -> AccountDetail:
    listing_id = str(listing.get("listingId", ""))
    metrics = _metrics_by_listing_id().get(listing_id, {})
    skin_names = _skin_names_for_listing(listing_id)
    hero_names = _hero_names_for_listing(listing_id)
    rank = _rank_text(listing)
    server_code = str(listing.get("serverCode", ""))
    tags = _tags_for_listing(listing, metrics)
    risk_level, risk_notes = _risk_for_listing(listing)

    return AccountDetail(
        id=listing_id,
        account_id=str(listing.get("accountId", "")),
        title=_title_for_listing(listing, metrics),
        price=int(listing.get("salePrice", 0)),
        platform=PLATFORM_LABELS.get(server_code, ""),
        server=SERVER_LABELS.get(server_code, server_code),
        rank=rank,
        cover_image=None,
        tags=tags,
        assets=AccountAssets(
            heroes=int(metrics.get("heroCount", len(hero_names))),
            skins=int(metrics.get("skinCount", len(skin_names))),
            rare_skins=skin_names[:5],
            currencies={
                "vip_level": int(listing.get("vipLevel", 0) or 0),
            },
        ),
        risk=AccountRisk(
            level=risk_level,
            notes=risk_notes,
        ),
        purchase_tips=_purchase_tips(listing, metrics),
    )


def _metrics_by_listing_id() -> dict[str, dict[str, Any]]:
    return {str(row.get("listingId", "")): row for row in load_tag_rows("accountMetrics.json")}


def _skin_names_for_listing(listing_id: str) -> list[str]:
    skin_by_id = {
        str(row.get("skinId", "")): str(row.get("skinName", ""))
        for row in load_tag_rows("skinMaster.json")
    }
    names = []
    for row in load_tag_rows("accountSkin.json"):
        if row.get("listingId") != listing_id:
            continue
        skin_name = skin_by_id.get(str(row.get("skinId", "")))
        if skin_name:
            names.append(skin_name)
    return names


def _hero_names_for_listing(listing_id: str) -> list[str]:
    hero_by_id = {
        str(row.get("heroId", "")): str(row.get("heroName", ""))
        for row in load_tag_rows("heroMaster.json")
    }
    names = []
    for row in load_tag_rows("accountHero.json"):
        if row.get("listingId") != listing_id:
            continue
        hero_name = hero_by_id.get(str(row.get("heroId", "")))
        if hero_name:
            names.append(hero_name)
    return names


def _title_for_listing(listing: dict[str, Any], metrics: dict[str, Any]) -> str:
    server = SERVER_LABELS.get(str(listing.get("serverCode", "")), "未知区服")
    rank = _rank_text(listing)
    vip_level = int(listing.get("vipLevel", 0) or 0)
    skin_count = int(metrics.get("skinCount", 0) or 0)
    return f"{server} · {rank} · V{vip_level} · {skin_count}皮肤账号"


def _rank_text(listing: dict[str, Any]) -> str:
    rank_name = str(listing.get("rankName", "") or "未知段位")
    rank_stars = int(listing.get("rankStars", 0) or 0)
    if rank_stars:
        return f"{rank_name}{rank_stars}星"
    return rank_name


def _tags_for_listing(listing: dict[str, Any], metrics: dict[str, Any]) -> list[str]:
    tags = [
        SERVER_LABELS.get(str(listing.get("serverCode", "")), ""),
        _rank_text(listing),
        f"V{int(listing.get('vipLevel', 0) or 0)}",
        f"{int(metrics.get('skinCount', 0) or 0)}皮肤",
        f"{int(metrics.get('heroCount', 0) or 0)}英雄",
        CHANGE_BIND_LABELS.get(str(listing.get("changeBindStatus", "")), ""),
        SECONDARY_REAL_NAME_LABELS.get(str(listing.get("secondaryRealNameStatus", "")), ""),
    ]
    return [tag for tag in tags if tag]


def _risk_for_listing(listing: dict[str, Any]) -> tuple[str, list[str]]:
    anti_addiction = str(listing.get("antiAddictionStatus", ""))
    secondary_real_name = str(listing.get("secondaryRealNameStatus", ""))
    change_bind = str(listing.get("changeBindStatus", ""))
    notes = [
        ANTI_ADDICTION_LABELS.get(anti_addiction, anti_addiction or "防沉迷状态未知"),
        SECONDARY_REAL_NAME_LABELS.get(secondary_real_name, secondary_real_name or "实名状态未知"),
        CHANGE_BIND_LABELS.get(change_bind, change_bind or "换绑状态未知"),
    ]

    if change_bind == "NOT_SUPPORTED" or secondary_real_name == "NOT_SUPPORTED":
        return "high", notes
    if anti_addiction == "RESTRICTED":
        return "medium", notes
    return "low", notes


def _purchase_tips(listing: dict[str, Any], metrics: dict[str, Any]) -> list[str]:
    _, risk_notes = _risk_for_listing(listing)
    value_score = float(metrics.get("valueScore", 0) or 0)
    tips = [*risk_notes]
    if value_score:
        tips.append(f"性价比评分：{value_score:.2f}")
    tips.append("下单前建议核对账号截图、可换绑状态和平台担保交易规则。")
    return tips


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]
