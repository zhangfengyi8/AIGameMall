"""
查询账号详情。
"""
from pathlib import Path
import json


def get_accounts_by_ids(ids: list[str]) -> list[dict]:
    """根据 ID 列表从 JSON 中查询账号详情"""
    accounts_path = Path(__file__).resolve().parent.parent.parent.parent.parent / "data" / "accounts" / "accounts.json"
    with open(str(accounts_path), encoding="utf-8-sig") as f:
        all_accounts = json.load(f)

    id_set = set(ids)
    found = [acc for acc in all_accounts if acc["id"] in id_set]

    # 按传入的 ID 顺序排序
    id_order = {aid: i for i, aid in enumerate(ids)}
    found.sort(key=lambda a: id_order.get(a["id"], 999))

    return found


def format_card(account: dict) -> dict:
    """将账号数据格式化为前端推荐卡片"""
    return {
        "account_id": account["id"],
        "title": account["title"],
        "game_name": account.get("game", {}).get("name", ""),
        "category": account.get("category", ""),
        "price": account.get("price", 0),
        "fair_price": account.get("valuation", {}).get("fair_price", 0),
        "value_label": account.get("valuation", {}).get("value_label", ""),
        "risk_label": account.get("risk", {}).get("label", ""),
        "rank": account.get("rank", {}).get("current", ""),
        "hero_count": account.get("account_assets", {}).get("hero_count", 0),
        "skin_count": account.get("account_assets", {}).get("skin_count", 0),
        "highlight_tags": account.get("highlights", {}).get("tags", []),
    }
