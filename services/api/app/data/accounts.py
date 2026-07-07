import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.schemas.accounts import AccountAssets, AccountDetail, AccountRisk


@lru_cache(maxsize=1)
def load_display_accounts() -> tuple[dict[str, Any], ...]:
    data_path = _repo_root() / "data" / "accounts" / "accounts.json"
    with data_path.open("r", encoding="utf-8-sig") as data_file:
        payload = json.load(data_file)

    if not isinstance(payload, list):
        return ()

    return tuple(account for account in payload if isinstance(account, dict))


@lru_cache(maxsize=1)
def load_listing_rows() -> tuple[dict[str, Any], ...]:
    data_path = _repo_root() / "data" / "tags" / "accountListing.json"
    with data_path.open("r", encoding="utf-8") as data_file:
        payload = json.load(data_file)

    if not isinstance(payload, list):
        return ()

    return tuple(row for row in payload if isinstance(row, dict))


def get_account_detail(account_id: str) -> AccountDetail | None:
    resolved_account_id = _resolve_account_id(account_id)
    for account in load_display_accounts():
        if account.get("id") == resolved_account_id:
            return _to_account_detail(requested_id=account_id, account=account)

    return None


def _resolve_account_id(account_id: str) -> str:
    for row in load_listing_rows():
        if row.get("listingId") == account_id:
            return str(row.get("accountId", account_id))

    return account_id


def _to_account_detail(*, requested_id: str, account: dict[str, Any]) -> AccountDetail:
    assets = account.get("account_assets", {})
    highlights = account.get("highlights", {})
    trade = account.get("trade", {})
    risk = account.get("risk", {})
    valuation = account.get("valuation", {})
    return AccountDetail(
        id=requested_id,
        account_id=str(account.get("id", "")),
        title=str(account.get("title", "")),
        price=int(account.get("price", 0)),
        platform=str(trade.get("platform", "")),
        server=str(trade.get("region", "")),
        rank=str(account.get("rank", {}).get("current", "")),
        cover_image=account.get("display", {}).get("cover_url") or None,
        tags=[str(tag) for tag in highlights.get("tags", [])],
        assets=AccountAssets(
            heroes=int(assets.get("hero_count", 0)),
            skins=int(assets.get("skin_count", 0)),
            rare_skins=[str(skin) for skin in highlights.get("skins", [])],
            currencies={
                "vip_level": int(assets.get("vip_level", 0)),
                "account_level": int(assets.get("account_level", 0)),
            },
        ),
        risk=AccountRisk(
            level=str(risk.get("level", "")),
            notes=[str(item) for item in risk.get("items", [])]
            + [str(item) for item in risk.get("warnings", [])],
        ),
        purchase_tips=[
            str(trade.get("bind_status", "")),
            str(trade.get("real_name_status", "")),
            str(valuation.get("valuation_note", "")),
        ],
    )


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]
