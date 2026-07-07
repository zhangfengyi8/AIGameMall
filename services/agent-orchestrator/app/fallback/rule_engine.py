"""
规则降级引擎：当模型不可用时，用关键词提取条件并返回模板推荐。
"""
import re

from app.tools.search import _do_search


def extract_intent(text: str) -> dict:
    """
    从用户文本中用关键词提取搜索条件。

    Returns:
        可直接传给 search_accounts 的参数 dict
    """
    params: dict = {}
    text_lower = text.lower()

    # 提取预算
    budget_pattern = re.compile(
        r"(\d+)\s*[块元]|预算[约大概]?(\d+)|(\d+)\s*以内|(\d+)\s*以下"
    )
    budgets = budget_pattern.findall(text)
    if budgets:
        max_budget = None
        for b in budgets:
            vals = [int(x) for x in b if x]
            if vals:
                v = vals[0]
                if max_budget is None or v > max_budget:
                    max_budget = v
        if max_budget is not None:
            params["budget_max"] = max_budget

    # 提取游戏
    if any(kw in text_lower for kw in ["王者荣耀", "王者", "农药", "honor of kings"]):
        params["game_id"] = "honor_of_kings"

    # 提取分类
    category_map = {
        "皮肤号": ["皮肤"],
        "氪佬号": ["氪佬", "顶配", "神号"],
        "技术号": ["技术", "战力", "国服"],
        "低价号": ["低价", "入门", "便宜"],
        "收藏号": ["收藏", "绝版"],
    }
    for cat, keywords in category_map.items():
        if any(kw in text_lower for kw in keywords):
            params["category"] = cat
            break

    # 提取英雄
    known_heroes = [
        "孙尚香", "李白", "貂蝉", "鲁班七号", "铠", "武则天",
        "孙悟空", "花木兰", "韩信", "后羿", "赵云", "瑶", "大乔", "镜", "马超",
    ]
    matched_heroes = [h for h in known_heroes if h in text]
    if matched_heroes:
        params["heroes"] = matched_heroes

    # 提取皮肤
    known_skins = [
        "杀手不太冷", "末日机甲", "仲夏夜之梦", "凤求凰", "至尊宝",
        "倪克斯神谕", "天鹅之梦", "全息碎影", "白龙吟", "地狱火",
        "遇见神鹿", "炽阳神光",
    ]
    matched_skins = [s for s in known_skins if s in text]
    if matched_skins:
        params["skins"] = matched_skins

    # 提取标签
    if any(kw in text_lower for kw in ["全英雄"]):
        params.setdefault("tags", [])
        params["tags"].append("全英雄")
    if any(kw in text_lower for kw in ["低风险", "风险低", "安全"]):
        params.setdefault("tags", [])
        params["tags"].append("低风险")
    if any(kw in text_lower for kw in ["可换绑", "换绑"]):
        params.setdefault("tags", [])
        params["tags"].append("可换绑")

    # 提取段位
    rank_map = {
        "青铜": 1, "白银": 2, "黄金": 3, "铂金": 5,
        "钻石": 7, "星耀": 10, "王者": 15, "荣耀王者": 22,
    }
    for rank_name, score in rank_map.items():
        if rank_name in text:
            params["rank_min"] = score
            break

    return params


def generate_fallback_reply(
    accounts: list[dict], user_text: str
) -> str:
    """根据搜索结果生成模板推荐回复。"""
    if not accounts:
        return (
            "抱歉，暂时没有找到完全符合你要求的账号。"
            "你可以试试放宽预算或者调整一下条件。"
        )

    lines = [f"为你推荐以下 {len(accounts[:3])} 个账号：\n"]
    for i, acc in enumerate(accounts[:3], 1):
        title = acc.get("title", "未知")
        price = acc.get("price", 0)
        rank = acc.get("rank", {}).get("current", "未知")
        value_label = acc.get("valuation", {}).get("value_label", "")
        risk_label = acc.get("risk", {}).get("label", "")
        skin_count = acc.get("account_assets", {}).get("skin_count", 0)

        lines.append(
            f"{i}. {title}"
            f"\n   价格：{price}元"
            f"\n   段位：{rank}"
            f"\n   皮肤数：{skin_count}"
            f"\n   性价比：{value_label}  风险：{risk_label}"
        )

        # 风险提示
        warnings = acc.get("risk", {}).get("warnings", [])
        if warnings:
            lines.append(f"   注意：{'；'.join(warnings)}")

        lines.append("")

    return "\n".join(lines)


def run_fallback(user_message: str) -> dict:
    """
    规则降级入口：提取条件 -> 搜索 -> 生成回复

    Returns:
        与 run_agent() 一致的返回结构
    """
    intent = extract_intent(user_message)
    accounts = _do_search(**intent)
    reply = generate_fallback_reply(accounts, user_message)

    return {
        "reply": reply,
        "history": [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": reply},
        ],
    }
