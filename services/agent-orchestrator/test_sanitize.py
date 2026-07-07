import sys, re
sys.stdout.reconfigure(encoding='utf-8')

def sanitize(text):
    replacements = {
        'listingId': '商品编号',
        'accountId': '账号编号',
        'serverCode': '区服',
        'gameCode': '游戏',
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    text = re.sub(r'\blisting[_-]?\d+\b', '该账号', text, flags=re.IGNORECASE)
    text = re.sub(r'\bacc[_-]?\d+\b', '该账号', text, flags=re.IGNORECASE)
    _SERVER_CODE_MAP = {
        'ANDROID_QQ': '安卓QQ',
        'ANDROID_WECHAT': '安卓微信',
        'IOS_QQ': '苹果QQ',
        'IOS_WECHAT': '苹果微信',
    }
    for _code, _name in _SERVER_CODE_MAP.items():
        text = text.replace(_code, _name)
    return text.strip()

test = '为你推荐以下 3 个账号：\n\n1. listing_10012 [IOS_WECHAT]\n   价格：120元'
sanitized = sanitize(test)
print('SANITIZED:')
print(sanitized)
print()
if 'listing_10012' not in sanitized and 'IOS_WECHAT' not in sanitized:
    print('SUCCESS: No internal IDs remain')
else:
    print('FAIL: Internal IDs still present')
    for p in ['listing_', 'listingId', 'IOS_WECHAT', 'ANDROID_QQ']:
        if p in sanitized:
            print(f'  - {p}')
