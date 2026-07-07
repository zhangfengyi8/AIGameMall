"""
buyer-requirement-intake skill 的 Python 实现。
职责：将用户自然语言需求转化为结构化槽位（slots），判断是否可推荐，需要时生成追问。
"""

import re

_RANK_ORDER = ["青铜", "白银", "黄金", "铂金", "钻石", "星耀", "王者", "无双王者", "荣耀王者"]

_KNOWN_HEROES = [
    "孙尚香", "李白", "貂蝉", "鲁班七号", "铠", "武则天",
    "孙悟空", "花木兰", "韩信", "后羿", "赵云", "瑶", "大乔", "镜", "马超",
    "诸葛亮", "小乔", "安琪拉", "妲己", "王昭君", "吕布", "澜", "曜",
    "上官婉儿", "西施", "弈星", "周瑜", "张良", "蒙犽", "戈娅", "海月",
    "司空震", "云缨", "赵怀真", "姬小满", "亚连", "少司缘", "大司命",
]

_KNOWN_SKINS = [
    "杀手不太冷", "末日机甲", "仲夏夜之梦", "凤求凰", "至尊宝",
    "倪克斯神谕", "天鹅之梦", "全息碎影", "白龙吟", "地狱火",
    "遇见神鹿", "炽阳神光",
]


def _find_platform(text: str) -> dict:
    text_lower = text.lower().replace(" ", "")
    if "qq" in text_lower or "q区" in text:
        login_channel = "QQ"
    elif "微信" in text or "wx" in text_lower or "wechat" in text_lower:
        login_channel = "WX"
    else:
        login_channel = None

    if "安卓" in text or "android" in text_lower:
        os_val = "安卓"
    elif "苹果" in text or "ios" in text_lower or "iphone" in text_lower:
        os_val = "iOS"
    else:
        os_val = None

    server_code = None
    if login_channel == "QQ" and os_val == "安卓":
        server_code = "ANDROID_QQ"
    elif login_channel == "QQ" and os_val == "iOS":
        server_code = "IOS_QQ"
    elif login_channel == "WX" and os_val == "安卓":
        server_code = "ANDROID_WECHAT"
    elif login_channel == "WX" and os_val == "iOS":
        server_code = "IOS_WECHAT"

    return {"login_channel": login_channel, "os": os_val, "server_code": server_code}


def _find_budget(text: str) -> dict:
    result = {"min": None, "max": None, "currency": "CNY", "flexible": False, "raw_text": None}
    nums = [int(v) for v in re.findall(r"(\d+)", text) if int(v) < 100000]
    if not nums:
        return result

    flexible = bool(re.search(r"左右|可加|能浮动|多一点|往上|上下|浮动", text))

    range_m = re.search(r"(\d+)\s*[-\u2013~\u2014]\s*(\d+)", text)
    if range_m:
        a, b = int(range_m.group(1)), int(range_m.group(2))
        result["min"] = min(a, b)
        result["max"] = max(a, b)
        result["flexible"] = flexible
        result["raw_text"] = text
        return result

    if re.search(r"不超过|以内|以下|最多|封顶|预算", text):
        result["max"] = max(nums)
        result["flexible"] = flexible
        result["raw_text"] = text
        return result

    if re.search(r"至少|以上|起步|最低", text):
        result["min"] = min(nums)
        result["flexible"] = flexible
        result["raw_text"] = text
        return result

    result["max"] = max(nums)
    result["flexible"] = flexible or bool(re.search(r"左右|上下", text))
    result["raw_text"] = text
    return result


def _find_rank(text: str) -> dict:
    result = {"current": None, "peak": None, "peak_score": None, "raw_text": None}
    for rank in _RANK_ORDER:
        if rank in text:
            result["current"] = rank
            result["raw_text"] = rank
            break
    return result


def _find_heroes(text: str) -> dict:
    found = [h for h in _KNOWN_HEROES if h in text]
    return {"must_have": found, "preferred": [], "lanes": []}


def _find_skins(text: str) -> dict:
    found = [s for s in _KNOWN_SKINS if s in text]
    quality = []
    if "传说" in text: quality.append("传说")
    if "史诗" in text: quality.append("史诗")
    if "限定" in text: quality.append("限定")
    if "典藏" in text: quality.append("典藏")
    count_pref = "high" if ("皮肤多" in text or "皮肤多点" in text) else None
    return {"must_have": found, "preferred": [], "quality": quality, "tags": [], "count_preference": count_pref}


def _find_risk_preference(text: str) -> dict:
    result = {"real_name_requirement": None, "retrieval_risk_tolerance": None,
              "requires_platform_guarantee": None, "raw_text": None}
    if "包不找回" in text or "安全" in text or "担保" in text or "低风险" in text:
        result["retrieval_risk_tolerance"] = "low"
        result["requires_platform_guarantee"] = True
    elif "二手机" in text or "找回号" in text or "不介意" in text:
        result["retrieval_risk_tolerance"] = "high"
    if "实名" in text or "二次" in text:
        result["real_name_requirement"] = text
    result["raw_text"] = text
    return result


def intake(text: str) -> dict:
    """执行买家需求理解，返回符合 SKILL.md Output Contract 的结构化结果。"""
    platform = _find_platform(text)
    budget = _find_budget(text)
    rank = _find_rank(text)
    heroes = _find_heroes(text)
    skins = _find_skins(text)
    risk = _find_risk_preference(text)

    account_goal = []
    if "皮肤" in text:
        account_goal.append("skin_collection")
    if "段位" in text or "排位" in text or "王者" in text:
        account_goal.append("rank_climb")
    if "战力" in text:
        account_goal.append("combat_power")
    if "性价比" in text:
        account_goal.append("value_for_money")
    if "英雄" in text or heroes["must_have"]:
        account_goal.append("hero_pool")
    if "贵族" in text or "vip" in text.lower():
        account_goal.append("noble_level")

    slots = {
        "game": "王者荣耀",
        "platform": {"login_channel": platform["login_channel"], "os": platform["os"], "server_code": platform.get("server_code"), "raw_text": None},
        "budget": budget,
        "account_goal": account_goal,
        "rank": rank,
        "heroes": heroes,
        "skins": skins,
        "assets": {"noble_level": None, "inscriptions": None, "hero_count": None,
                     "skin_count": None, "glory_crystal": None, "other": []},
        "risk_preference": risk,
        "deal_preference": {"price_first": "性价比" in text,
                              "asset_first": "毕业" in text or "多多" in text or "最好" in text,
                              "same_platform_first": False, "acceptable_missing_items": []},
    }

    firm = []
    soft = []
    if budget.get("max") is not None:
        (soft if budget.get("flexible") else firm).append(f"预算不超过{budget['max']}元")
    if budget.get("min") is not None:
        firm.append(f"预算不低于{budget['min']}元")
    if platform.get("login_channel"):
        firm.append(f"登录渠道：{platform['login_channel']}")
    if platform.get("os"):
        firm.append(f"系统：{platform['os']}")
    if heroes["must_have"]:
        firm.append(f"英雄：{'、'.join(heroes['must_have'])}")
    if skins["must_have"]:
        firm.append(f"皮肤：{'、'.join(skins['must_have'])}")
    if rank.get("current"):
        soft.append(f"段位：{rank['current']}")
    if skins.get("count_preference") == "high" or "皮肤多" in text:
        soft.append("皮肤数量多")
    if "性价比" in text:
        soft.append("高性价比")

    missing_required = []
    if budget.get("max") is None and budget.get("min") is None:
        missing_required.append("budget")

    missing_optional = []
    if not platform.get("login_channel") and not platform.get("os"):
        missing_optional.append("platform")
    if not rank.get("current"):
        missing_optional.append("rank")

    ready = budget.get("max") is not None or budget.get("min") is not None

    clarifying = ""
    if not ready:
        clarifying = "预算大概多少？最高能接受到多少？"
    elif not platform.get("login_channel") and not platform.get("os") and ready:
        clarifying = "你要 QQ 还是微信，安卓还是 iOS？"

    return {
        "intent": "buy_account",
        "confidence": 0.8 if ready else 0.4,
        "slots": slots,
        "firm_requirements": firm,
        "soft_preferences": soft,
        "missing_required_slots": missing_required,
        "missing_optional_slots": missing_optional,
        "clarifying_question": clarifying,
        "ready_for_recommendation": ready,
        "notes": [],
    }


def search_params_from_intake(intake_result: dict) -> dict:
    """将 intake 结果转换为 search_accounts 的参数。"""
    slots = intake_result["slots"]
    params = {"game_code": "WZ"}
    sc = slots["platform"].get("server_code")
    if sc:
        params["server_code"] = sc
    budget = slots["budget"]
    if budget.get("max") is not None:
        params["budget_max"] = budget["max"] * 100
    if budget.get("min") is not None:
        params["budget_min"] = budget["min"] * 100
    if slots["heroes"]["must_have"]:
        params["heroes"] = slots["heroes"]["must_have"]
    if slots["skins"]["must_have"]:
        params["skins"] = slots["skins"]["must_have"]
    if slots["rank"].get("current"):
        params["rank_name"] = slots["rank"]["current"]
    return params
