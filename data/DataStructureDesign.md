账号业务数据结构
一、账号商品表
accountListing
|字段|中文名称|类型|必填|示例及规则|
|listingId|商品ID|String|是|listing_10001，全局唯一|
|accountId|游戏营地ID|String|是|1729198306，必须用字符串|
|gameCode|游戏编码|Enum|是|WZ|
|serverCode|区服编码|Enum|是|IOS_QQ|
|salePrice|商品售价|Integer|是|188800，代表 1888 元|
|antiAddictionStatus|防沉迷状态|Enum|是|NONE|
|secondaryRealNameStatus|二次实名状态|Enum|是|NOT_SUPPORTED|
|changeBindStatus|换绑支持状态|Enum|是|FULL_SUPPORTED|
|vipLevel|贵族等级|Integer|否|7，前端展示为“V7贵族”|
|rankName|当前段位|String|否|无双王者|
|rankStars|当前星数|Integer|否|12|
|winRate|胜率|Decimal|否|53.41，取值范围 0～100|

账号状态枚举
|字段|枚举值|中文名称|
|antiAddictionStatus|NONE|无防沉迷|
|antiAddictionStatus|RESTRICTED|有防沉迷限制|
|secondaryRealNameStatus|SUPPORTED|支持二次实名|
|secondaryRealNameStatus|NOT_SUPPORTED|不支持二次实名|
|changeBindStatus|FULL_SUPPORTED|支持换绑|
|changeBindStatus|NOT_SUPPORTED|不支持换绑|

区服枚举
|serverCode|前端名称|
|IOS_QQ|苹果QQ|
|IOS_WECHAT|苹果微信|
|ANDROID_QQ|安卓QQ|
|ANDROID_WECHAT|安卓微信|

二、英雄主数据表
heroMaster
|字段|中文名称|类型|必填|示例及规则|
|heroId|英雄ID|String|是|hero_gong_ben_wu_zang，全局唯一|
|heroName|英雄名称|String|是|宫本武藏|
|aliases|英雄别名|Array<String>|否|["宫本"]，用于自然语言检索|
|roleCodes|英雄职业|Array<Enum>|是|["WARRIOR"]|
|laneCodes|常用分路|Array<Enum>|是|["JUNGLE","CLASH_LANE"]|
|imageUrl|英雄图片|String|否|HTTPS 图片地址|

英雄职业枚举
|roleCode|中文名称|检索同义词示例|
|TANK|坦克|肉、前排、扛伤|
|WARRIOR|战士|战边、近战|
|ASSASSIN|刺客|收割、爆发刺客|
|MAGE|法师|法系、法伤|
|MARKSMAN|射手|ADC、远程物理|
|SUPPORT|辅助|奶妈、开团辅助|

英雄分路枚举
|laneCode|中文名称|检索同义词示例|
|CLASH_LANE|对抗路|上单、边路|
|MID_LANE|中路|中单|
|FARM_LANE|发育路|下路|
|JUNGLE|打野|野区|
|ROAM|游走|辅助位|

英雄数据录入示例
|heroId|heroName|aliases|roleCodes|laneCodes|
|hero_liu_bei|刘备|[]|["WARRIOR"]|["JUNGLE","CLASH_LANE"]|
|hero_gong_ben_wu_zang|宫本武藏|["宫本"]|["WARRIOR"]|["JUNGLE","CLASH_LANE"]|
|hero_li_bai|李白|[]|["ASSASSIN"]|["JUNGLE"]|
|hero_lu_na|露娜|[]|["MAGE","ASSASSIN"]|["JUNGLE","CLASH_LANE"]|
|hero_zhang_liang|张良|[]|["MAGE"]|["MID_LANE"]|
|hero_lian_po|廉颇|[]|["TANK"]|["CLASH_LANE","ROAM"]|
|hero_hou_yi|后羿|[]|["MARKSMAN"]|["FARM_LANE"]|
|hero_cai_wen_ji|蔡文姬|[]|["SUPPORT"]|["ROAM"]|

三、皮肤主数据表
skinMaster
|字段|中文名称|类型|必填|示例及规则|
|skinId|皮肤ID|String|是|skin_gongben_diyuzhiyan|
|skinName|皮肤名称|String|是|地狱之眼|
|aliases|皮肤别名|Array<String|否|用于简称检索|
|heroId|所属英雄ID|String|是|hero_gong_ben_wu_zang|
|qualityCode|皮肤基础品质|Enum|是|LEGEND|
|tagCodes|皮肤标签|Array|否|FMVP|
|seriesCode|皮肤系列编码|String|否|SAINT_SEIYA|
|referenceValueFen|参考价值|Integer|否|皮肤发售价格|
|imageUrl|皮肤图片|String|否|HTTPS 图片地址|

皮肤品质枚举
|qualityCode|中文名称|皮肤价值|
|OTHER|其他| |
|RARE|勇者| |
|EPIC|史诗| |
|LENGEND|传说| |
|FINE_TREASURE|珍品| |
|COLLECTION|典藏| |

 皮肤数据录入示例
|skinId|skinName|heroId|qualityCode|tagCodes|
|skin_gongben_diyuzhiyan|地狱之眼|hero_gong_ben_wu_zang|LEGEND|FMVP|
| | | | | |

三、账号资产关联表
账号拥有英雄关系表
accountHero
|字段|中文名称|类型|必填|示例|
|listingId|商品ID|String|是|listing_10001|
|heroId|英雄ID|String|是|hero_li_bai|

账号拥有皮肤关系表
accountSkin
|字段|中文名称|类型|必填|示例|
|listingId|商品ID|String|是|listing_10001|
|skinId|皮肤ID|String|是|skin_gongben_diyuzhiyan|

四、荣耀称号
accountHonor
|字段|中文名称|类型|必填|示例及规则|
|honorId|称号记录ID|String|是| |
|listingId|商品ID|String|是|listing_10001|
|heroId|对应英雄ID|String|是|hero_liu_bei|
|regionCode|地区编码|String|否|标准地区编码|
|regionName|地区名称快照|String|是|克州|
|ranking|地区排名|Integer|是|40，必须大于 0|
|titleLevelCode|称号等级|Enum|否|CITY|

称号等级枚举
|titleLevelCode|中文名称|
|DISTRICT|区／县级|
|CITY|市级|
|PROVINCE|省级|
|NATIONAL|国服|
|OTHER|其他|

五、账号检索指标表
accountMetrics
|字段|中文名称|类型|计算规则|
|listingId|商品ID|String|关联账号商品|
|skinCount|皮肤数量|Integer|accountSkin 去重计数|
|heroCount|英雄数量|Integer|accountHero 去重计数|
|skinTotalValueFen|皮肤参考总价值|Integer|所有皮肤 referenceValueFen 求和|
|heroSkinCounts|各英雄皮肤数量|Object|按 heroId 聚合|
|valueScore|性价比评分|Decimal|skinTotalValueFen/salePrice|