"""
T21n1299 宿曜經原典引用共用模組

所有原典引文的唯一來源。禁止在其他檔案直接寫入經文片段。
修改此檔即可全域更新所有引用。

CBETA: https://cbetaonline.dila.edu.tw/zh/T21n1299
"""

# ============================================================
# 品二 六關係日 (p.397c-398a)
# ============================================================
T21_HINNI = {
    # 栄日
    "ei": {
        "text": "宜入官拜職、對見大人、上書表進獻君王、興營買賣",
        "source": "T21 p.397c",
        "tone": "積極行動",
    },
    # 親日
    "shin": {
        "text": "宜結交、定婚姻、歡宴聚會並吉",
        "source": "T21 p.397c",
        "tone": "人際吉利",
    },
    # 業日
    "gyo": {
        "text": "所作善惡亦不成就，甚衰",
        "source": "T21 p.397c",
        "tone": "凶，不宜行事",
    },
    # 胎日
    "tai": {
        "text": "不宜舉動百事",
        "source": "T21 p.397c",
        "tone": "凶，靜守",
    },
    # 命日
    "mei": {
        "text": "不宜舉動百事",
        "source": "T21 p.397c",
        "supplement": "品三「宜修功德」(p.391b)",
        "tone": "靜守，修功德",
    },
    # 友日
    "yu": {
        "text": "宜結交朋友大吉",
        "source": "T21 p.391b",
        "tone": "人際吉利",
    },
    # 衰日
    "sui": {
        "text": "唯宜解除諸惡、療病",
        "source": "T21 p.398a",
        "taboo": "不宜出入遷移、買賣",
        "tone": "消極守成",
    },
    # 危日
    "ki": {
        "text": "宜結交、定婚姻，歡宴聚會並吉",
        "source": "T21 p.397c-398a",
        "taboo": "不宜遠行出入移徙、買賣、婚姻、裁衣、剃頭、沐浴並凶",
        "taboo_source": "T21 p.398a",
        "tone": "社交吉，遠行凶",
    },
    # 成日
    "sei": {
        "text": "宜修道學問、作諸成就法並吉",
        "source": "T21 p.398a",
        "supplement": "合和長年藥法",
        "tone": "修學吉利",
    },
    # 安日
    "an": {
        "text": "移徙吉、造作園宅並吉",
        "source": "T21 p.397c",
        "supplement": "安坐臥床帳吉",
        "tone": "安穩吉利",
    },
    # 壊日
    "kai": {
        "text": "宜作鎮壓、降伏怨讎，餘並不堪",
        "source": "T21 p.398a",
        "tone": "僅降伏可，餘凶",
    },
}

# ============================================================
# 品八 七曜五行 (p.399a)
# ============================================================
T21_SHICHIYOU = {
    "framework": {
        "text": "七曜直日",
        "source": "T21 p.399a",
        "note": "品八記載七曜各主一元素，五行相生相剋為運算基礎",
    },
    "ragosei": {
        "text": "羅喉為蝕神",
        "source": "T21 p.399a",
    },
    "keitosei": {
        "text": "計都為蝕神",
        "source": "T21 p.399a",
    },
    "nichiyou": {
        "text": "日曜為天體之首",
        "source": "T21 p.399a",
    },
    "getsuyou": {
        "text": "月曜為夜之主",
        "source": "T21 p.399a",
    },
}

# ============================================================
# 品三 凌犯 (p.391b-c)
# ============================================================
T21_RYOUHAN = {
    "reversal": {
        "text": "凌犯期間吉凶逆轉",
        "source": "T21 p.391b-c",
    },
    "remedy": {
        "text": "宜修功德、入灌頂及護摩，並修諸功德",
        "source": "T21 p.391b-c",
    },
}

# ============================================================
# 特殊日 (p.398b-c)
# ============================================================
T21_SPECIAL = {
    "kanro": {
        "text": "甘露日",
        "source": "T21 p.398b",
    },
    "kongou": {
        "text": "宜作一切降伏法，誦日天子呪及作護摩，並諸猛利等事",
        "source": "T21 p.398b-c",
    },
    "rasetsu": {
        "text": "不宜舉百事，必有殃禍",
        "source": "T21 p.398c",
    },
}

# ============================================================
# 非 T21 來源標籤
# ============================================================
SOURCES = {
    "gogyou": "品八七曜五行（T21 p.399a）",
    "gogyou_short": "T21 p.399a",
    "temple": "宿曜道寺院傳承：放生寺/大聖院/岡寺",
    "temple_short": "寺院傳承",
    "shukuyoudou": "宿曜道傳承",
    "editor": "編者歸納",
    "kuyou_cycle": "九曜循環流年法",
}

# ============================================================
# 六關係 → 引用鍵對照
# ============================================================
RELATION_CITE_MAP = {
    "eishin": ["ei", "shin"],
    "gyotai": ["gyo", "tai"],
    "mei": ["mei"],
    "yusui": ["yu", "sui"],
    "kisei": ["ki", "sei"],
    "ankai": ["an", "kai"],
}

# 五行關係 → 來源標籤
ELEMENT_RELATION_SOURCE = {
    "same": f"七曜五行同元素共振（T21 p.399a）",
    "generating": f"七曜五行相生（T21 p.399a）",
    "weakening": "七曜五行相洩",
    "conflicting": "七曜五行相剋",
    "neutral": "干支五行中性",
}


# 六關係短標籤（用於動態生成的簡短引用）
RELATION_TAG = {
    "eishin": "栄親日（T21 p.397c）",
    "gyotai": "業胎日（T21 p.397c）",
    "mei": "命日（T21 p.397c）",
    "yusui": "友衰日（T21 p.397c-398a）",
    "kisei": "危成日（T21 p.397c-398a）",
    "ankai": "安壊日（T21 p.397c-398a）",
}

# 九曜來源短標籤
KUYOU_TAG = "九曜循環（寺院傳承）"

# 凌犯來源短標籤
RYOUHAN_TAG = "凌犯（T21 品三 p.391b-c）"

# 暗黒の一週間來源短標籤（品二各日吉凶）
DARK_WEEK_TAG = "品二各日吉凶（T21 p.397c-398a）"

# 三期日型來源短標籤
SANKI_TAG = "三九秘法（T21 品二 p.397c-398a）"


# ============================================================
# 工具函數
# ============================================================

def cite(key: str, short: bool = False) -> str:
    """
    回傳品二格式化引用。

    cite("ei") → '原典記載「宜入官拜職、對見大人...」（T21 p.397c）'
    cite("ei", short=True) → '「宜入官拜職、對見大人...」（T21 p.397c）'
    """
    q = T21_HINNI[key]
    if short:
        return f"「{q['text']}」（{q['source']}）"
    return f"原典記載「{q['text']}」（{q['source']}）"


def cite_taboo(key: str) -> str:
    """回傳品二禁忌引用（如有）。"""
    q = T21_HINNI[key]
    taboo = q.get("taboo")
    if not taboo:
        return ""
    src = q.get("taboo_source", q["source"])
    return f"「{taboo}」（{src}）"


def cite_shichiyou(key: str = "framework") -> str:
    """回傳品八七曜引用。"""
    q = T21_SHICHIYOU[key]
    return f"「{q['text']}」（{q['source']}）"


def cite_special(key: str) -> str:
    """回傳特殊日引用。"""
    q = T21_SPECIAL[key]
    return f"「{q['text']}」（{q['source']}）"


def source_label(key: str) -> str:
    """回傳非 T21 來源標籤。"""
    return SOURCES[key]


def relation_tag(relation: str) -> str:
    """回傳六關係短標籤。relation_tag("eishin") → '栄親日（T21 p.397c）'"""
    return RELATION_TAG.get(relation, "")


def relation_cite(relation: str, short: bool = True) -> str:
    """
    根據六關係名回傳對應引用。

    relation_cite("eishin") → '栄日「宜入官...」（T21 p.397c）'
    """
    keys = RELATION_CITE_MAP.get(relation, [])
    if not keys:
        return ""
    parts = []
    names = {"ei": "栄日", "shin": "親日", "gyo": "業日", "tai": "胎日",
             "mei": "命日", "yu": "友日", "sui": "衰日", "ki": "危日",
             "sei": "成日", "an": "安日", "kai": "壊日"}
    for k in keys:
        q = T21_HINNI[k]
        parts.append(f"{names[k]}{cite(k, short=True)}")
    return "、".join(parts)


def element_source(relation: str) -> str:
    """回傳五行關係來源標籤。"""
    return ELEMENT_RELATION_SOURCE.get(relation, "")


def kuyou_source(star_element: str | None) -> str:
    """回傳九曜星來源標籤。"""
    cycle = SOURCES["kuyou_cycle"]
    temple = SOURCES["temple_short"]
    if star_element is None:
        # 羅喉/計都（蝕神）
        return f"{cycle}（{SOURCES['temple']}）"
    if star_element in ("日", "月"):
        return f"{cycle}（{temple}）"
    return f"品八七曜之{star_element}曜（T21 p.399a），{cycle}（{temple}）"
