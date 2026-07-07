"""
buyer-requirement-intake skill 的 Python 实现。
职责：将用户自然语言需求转化为结构化槽位（slots），判断是否可推荐，需要时生成追问。
"""

import re

_RANK_ORDER = ["荣耀王者", "无双王者", "王者", "星耀", "钻石", "铂金", "黄金", "白银", "青铜"]

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


def _first_int(patterns: list[str], text: str) -> int | None:
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None


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
    result = {"min": None, "max": None, "currency": "CNY", "flexible": False, "unlimited": False, "raw_text": None}
    if re.search(r"预算不限|不限预算|价格不限|不限价|不设预算|预算无上限|无预算上限", text):
        result["unlimited"] = True
        result["raw_text"] = text
        return result
    budget_text = re.sub(r"(?:vip|VIP|[vV]|贵族(?:等级)?|贵)\s*\d+", " ", text)
    budget_text = re.sub(r"\d+\s*星", " ", budget_text)
    budget_text = re.sub(r"(?:皮肤|皮|英雄|典藏|传说|限定)\s*\d+\s*(?:个|款|位)?", " ", budget_text)
    budget_text = re.sub(r"\d+\s*(?:个|款|位)?\s*(?:皮肤|英雄|典藏|传说|限定)", " ", budget_text)
    nums = [
        int(match.group(1))
        for match in re.finditer(r"(?<![A-Za-z0-9])(\d+)(?![A-Za-z0-9])", budget_text)
        if int(match.group(1)) < 100000
    ]
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
    result = {"current": None, "stars": None, "peak": None, "peak_score": None, "raw_text": None}
    for rank in _RANK_ORDER:
        if rank in text:
            result["current"] = rank
            result["raw_text"] = rank
            break
    stars = _first_int([r"(\d+)\s*星"], text)
    if stars is not None:
        result["stars"] = stars
        result["raw_text"] = text
        if result["current"] is None and "王者" in text:
            result["current"] = "王者"
    peak_score = _first_int([r"巅峰(?:赛)?(?:分|积分)?\s*(\d+)", r"(\d+)\s*巅峰分"], text)
    if peak_score is not None:
        result["peak_score"] = peak_score
        result["raw_text"] = text
    return result


def _find_heroes(text: str) -> dict:
    found = [h for h in _KNOWN_HEROES if h in text]
    return {"must_have": found, "preferred": [], "lanes": []}




def _resolve_hero_quality_skins(text: str) -> list[str]:
    import os, json
    _base_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))), "data", "tags")
    try:
        with open(os.path.join(_base_path, "skinMaster.json"), encoding="utf-8-sig") as _f:
            _sm = json.load(_f)
    except Exception:
        return []
    mentioned = [h for h in _KNOWN_HEROES if h in text]
    if not mentioned:
        return []
    qk = []
    if "典藏" in text or "荣耀典藏" in text:
        qk.append("荣耀典藏")
    if "传说" in text:
        qk.append("传说")
    if "限定" in text:
        qk.append("限定")
    if not qk:
        return []
    resolved = []
    for s in _sm:
        if s["heroName"] in mentioned and any(q in s.get("tagCodes", []) for q in qk):
            if s["skinName"] not in resolved:
                resolved.append(s["skinName"])
    return resolved
def _find_skins(text: str) -> dict:
    found = [s for s in _KNOWN_SKINS if s in text]
    # 解析英雄+品质组合（如"孙尚香荣耀典藏"），自动补充具体皮肤名
    resolved = _resolve_hero_quality_skins(text)
    for skin_name in resolved:
        if skin_name not in found:
            found.append(skin_name)
    quality = []
    if "传说" in text: quality.append("传说")
    if "史诗" in text: quality.append("史诗")
    if "限定" in text: quality.append("限定")
    if "典藏" in text: quality.append("典藏")
    count_pref = "high" if ("皮肤多" in text or "皮肤多点" in text) else None
    return {"must_have": found, "preferred": [], "quality": quality, "tags": [], "count_preference": count_pref}


def _find_assets(text: str) -> dict:
    noble_level = _first_int([
        r"(?:vip|VIP|[vV])\s*(\d+)",
        r"贵族(?:等级)?\s*(\d+)",
        r"贵\s*(\d+)",
    ], text)
    skin_count = _first_int([r"(?:皮肤|皮)\s*(\d+)\s*(?:个|款)?", r"(\d+)\s*(?:个|款)?皮肤"], text)
    hero_count = _first_int([r"(?:英雄)\s*(\d+)\s*(?:个|位)?", r"(\d+)\s*(?:个|位)?英雄"], text)
    collector_skin_count = _first_int([r"典藏\s*(\d+)\s*(?:个|款)?", r"(\d+)\s*(?:个|款)?典藏"], text)
    legend_skin_count = _first_int([r"传说\s*(\d+)\s*(?:个|款)?", r"(\d+)\s*(?:个|款)?传说"], text)
    limited_skin_count = _first_int([r"限定\s*(\d+)\s*(?:个|款)?", r"(\d+)\s*(?:个|款)?限定"], text)
    full_heroes = bool(re.search(r"全英雄|满英雄|英雄全", text))
    return {
        "noble_level": noble_level,
        "inscriptions": None,
        "hero_count": hero_count,
        "skin_count": skin_count,
        "legend_skin_count": legend_skin_count,
        "limited_skin_count": limited_skin_count,
        "collector_skin_count": collector_skin_count,
        "full_heroes": full_heroes,
        "glory_crystal": None,
        "other": [],
    }


def _find_risk_preference(text: str) -> dict:
    result = {"real_name_requirement": None, "retrieval_risk_tolerance": None,
              "requires_platform_guarantee": None, "anti_addiction_status": None,
              "secondary_real_name_status": None, "change_bind_status": None, "raw_text": None}
    if "包不找回" in text or "安全" in text or "担保" in text or "低风险" in text:
        result["retrieval_risk_tolerance"] = "low"
        result["requires_platform_guarantee"] = True
    elif "二手机" in text or "找回号" in text or "不介意" in text:
        result["retrieval_risk_tolerance"] = "high"
    if "实名" in text or "二次" in text:
        result["real_name_requirement"] = text
    if re.search(r"无防沉迷|不要防沉迷|没有防沉迷|防沉迷无|不限时", text):
        result["anti_addiction_status"] = "NONE"
    if re.search(r"二次实名|实名可改|可实名|支持实名|支持二次", text):
        result["secondary_real_name_status"] = "SUPPORTED"
    if re.search(r"可换绑|能换绑|支持换绑|完全换绑|换绑", text):
        result["change_bind_status"] = "FULL_SUPPORTED"
    result["raw_text"] = text
    return result


def intake(text: str) -> dict:
    """执行买家需求理解，返回符合 SKILL.md Output Contract 的结构化结果。"""
    platform = _find_platform(text)
    budget = _find_budget(text)
    rank = _find_rank(text)
    heroes = _find_heroes(text)
    skins = _find_skins(text)
    assets = _find_assets(text)
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
    if "贵族" in text or "vip" in text.lower() or assets["noble_level"] is not None:
        account_goal.append("noble_level")
    if assets["full_heroes"] or assets["hero_count"] is not None:
        account_goal.append("hero_pool")

    slots = {
        "game": "王者荣耀",
        "platform": {"login_channel": platform["login_channel"], "os": platform["os"], "server_code": platform.get("server_code"), "raw_text": None},
        "budget": budget,
        "account_goal": account_goal,
        "rank": rank,
        "heroes": heroes,
        "skins": skins,
        "assets": assets,
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
    if budget.get("unlimited"):
        soft.append("预算不限")
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
    if rank.get("stars") is not None:
        firm.append(f"王者星数不少于{rank['stars']}星")
    if rank.get("peak_score") is not None:
        firm.append(f"巅峰分不少于{rank['peak_score']}")
    if assets.get("noble_level") is not None:
        firm.append(f"贵族等级至少V{assets['noble_level']}")
    if assets.get("skin_count") is not None:
        firm.append(f"皮肤数量不少于{assets['skin_count']}个")
    if assets.get("hero_count") is not None:
        firm.append(f"英雄数量不少于{assets['hero_count']}个")
    if assets.get("collector_skin_count") is not None:
        firm.append(f"典藏皮肤不少于{assets['collector_skin_count']}个")
    if assets.get("legend_skin_count") is not None:
        firm.append(f"传说皮肤不少于{assets['legend_skin_count']}个")
    if assets.get("limited_skin_count") is not None:
        firm.append(f"限定皮肤不少于{assets['limited_skin_count']}个")
    if assets.get("full_heroes"):
        firm.append("全英雄")
    if risk.get("anti_addiction_status") == "NONE":
        firm.append("无防沉迷")
    if risk.get("secondary_real_name_status") == "SUPPORTED":
        firm.append("支持二次实名")
    if risk.get("change_bind_status") == "FULL_SUPPORTED":
        firm.append("支持换绑")
    if skins.get("count_preference") == "high" or "皮肤多" in text:
        soft.append("皮肤数量多")
    if "性价比" in text:
        soft.append("高性价比")

    has_budget = budget.get("max") is not None or budget.get("min") is not None or budget.get("unlimited")
    has_platform = bool(platform.get("login_channel") or platform.get("os"))
    has_specific_goal = bool(
        account_goal
        or heroes["must_have"]
        or skins["must_have"]
        or rank.get("current")
        or rank.get("stars") is not None
        or any(
            assets.get(key) is not None
            for key in (
                "noble_level",
                "hero_count",
                "skin_count",
                "legend_skin_count",
                "limited_skin_count",
                "collector_skin_count",
            )
        )
        or assets.get("full_heroes")
    )

    missing_required = []
    if not has_budget and not has_specific_goal:
        missing_required.append("budget_or_goal")

    missing_optional = []
    if not has_platform:
        missing_optional.append("platform")
    if not rank.get("current"):
        missing_optional.append("rank")

    ready = has_budget and has_platform

    clarifying = ""
    if not has_budget and has_platform:
        clarifying = "预算大概多少？或者你希望的价格范围是多少？"
    elif not has_budget and not has_platform:
        clarifying = "预算大概多少？你用 QQ 还是微信，安卓还是 iOS？"
    elif has_budget and not has_platform:
        clarifying = "请告诉我你用 QQ 还是微信，安卓还是 iOS？"

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
        params["budget_max"] = budget["max"]
    if budget.get("min") is not None:
        params["budget_min"] = budget["min"]
    if slots["heroes"]["must_have"]:
        params["heroes"] = slots["heroes"]["must_have"]
    if slots["skins"]["must_have"]:
        params["skins"] = slots["skins"]["must_have"]
    if slots["rank"].get("current"):
        params["rank_name"] = slots["rank"]["current"]
    if slots["rank"].get("stars") is not None:
        params["min_rank_stars"] = slots["rank"]["stars"]
    assets = slots["assets"]
    if assets.get("noble_level") is not None:
        params["min_vip_level"] = assets["noble_level"]
    if assets.get("skin_count") is not None:
        params["min_skin_count"] = assets["skin_count"]
    if assets.get("hero_count") is not None:
        params["min_hero_count"] = assets["hero_count"]
    if assets.get("collector_skin_count") is not None:
        params["min_collector_skin_count"] = assets["collector_skin_count"]
    if assets.get("legend_skin_count") is not None:
        params["min_legend_skin_count"] = assets["legend_skin_count"]
    if assets.get("limited_skin_count") is not None:
        params["min_limited_skin_count"] = assets["limited_skin_count"]
    if assets.get("full_heroes"):
        params["require_full_heroes"] = True
    risk = slots["risk_preference"]
    if risk.get("anti_addiction_status"):
        params["anti_addiction"] = risk["anti_addiction_status"]
    if risk.get("secondary_real_name_status"):
        params["secondary_real_name"] = risk["secondary_real_name_status"]
    if risk.get("change_bind_status"):
        params["change_bind"] = risk["change_bind_status"]
    return params
