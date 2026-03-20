"""宿曜道計算服務 - 日本真言宗占星術"""
import json
import random
from datetime import date
from pathlib import Path
from typing import Optional

from shukuyo.services.t21_citations import (
    cite,
    RELATION_TAG, RYOUHAN_TAG, DARK_WEEK_TAG, SANKI_TAG,
)


class SukuyodoService:
    """
    宿曜道（真言宗宿曜占星術）計算服務

    基於不空三藏譯《宿曜經》（T21 No.1299），使用農曆生日計算本命宿（27宿之一），
    並提供雙人相性診斷（六種關係）。
    """

    # 月宿傍通曆：農曆月份對應的起始宿
    # 每月初一從這個宿開始，之後每天進一宿
    MONTH_START_MANSION = {
        1: 11,   # 正月：室宿
        2: 13,   # 二月：奎宿
        3: 15,   # 三月：胃宿
        4: 17,   # 四月：畢宿
        5: 19,   # 五月：参宿
        6: 21,   # 六月：鬼宿
        7: 24,   # 七月：張宿
        8: 0,    # 八月：角宿
        9: 2,    # 九月：氐宿
        10: 4,   # 十月：心宿
        11: 7,   # 十一月：斗宿
        12: 9,   # 十二月：虛宿
    }

    # 距離類型對照表：用於判斷近距離/中距離/遠距離及方向性
    # 依據 yakumoin.net（八雲院）絕對距離分類：
    #   近距離 = abs_dist 0-4（含業/胎）→ d=0,1,2,3,4,9,18,23,24,25,26
    #   中距離 = abs_dist 5-8           → d=5,6,7,8,19,20,21,22
    #   遠距離 = abs_dist 10-13         → d=10,11,12,13,14,15,16,17
    # direction_map: 從 person1 角度看，該距離代表的方向（如 1 = 栄，26 = 親）
    DISTANCE_TYPE_MAP = {
        "eishin": {
            "near": {"distances": [1, 26], "direction_map": {1: "栄", 26: "親"}},
            "mid": {"distances": [8, 19], "direction_map": {8: "親", 19: "栄"}},
            "far": {"distances": [10, 17], "direction_map": {10: "栄", 17: "親"}}
        },
        "yusui": {
            "near": {"distances": [2, 25], "direction_map": {2: "衰", 25: "友"}},
            "mid": {"distances": [7, 20], "direction_map": {7: "友", 20: "衰"}},
            "far": {"distances": [11, 16], "direction_map": {11: "衰", 16: "友"}}
        },
        "ankai": {
            "near": {"distances": [3, 24], "direction_map": {3: "安", 24: "壊"}},
            "mid": {"distances": [6, 21], "direction_map": {6: "壊", 21: "安"}},
            "far": {"distances": [12, 15], "direction_map": {12: "安", 15: "壊"}}
        },
        "kisei": {
            "near": {"distances": [4, 23], "direction_map": {4: "危", 23: "成"}},
            "mid": {"distances": [5, 22], "direction_map": {5: "成", 22: "危"}},
            "far": {"distances": [13, 14], "direction_map": {13: "危", 14: "成"}}
        },
        "mei": {"near": {"distances": [0], "direction_map": {0: "命"}}},
        "gyotai": {
            "near": {"distances": [9, 18], "direction_map": {9: "業", 18: "胎"}}
        }
    }

    # === 關係類型 → 方位對照（用於從 CAREER_CANONICAL_MAP 動態組裝引文） ===
    RELATION_DIRECTIONS = {
        "eishin": ("栄", "親"),
        "yusui": ("友", "衰"),
        "ankai": ("安", "壊"),
        "kisei": ("危", "成"),
        "mei": ("命",),
        "gyotai": ("業", "胎"),
    }

    # === 原典三九秘法：位名對照 ===
    # distance 0-8 = 一九（命行）, 9-17 = 二九（業行）, 18-26 = 三九（胎行）
    # 各九的起始位不同（命/業/胎），後續 8 位（栄→衰→安→危→成→壊→友→親）共通
    SANKU_POSITION_NAMES = [
        "命", "栄", "衰", "安", "危", "成", "壊", "友", "親",  # 一九
        "業", "栄", "衰", "安", "危", "成", "壊", "友", "親",  # 二九
        "胎", "栄", "衰", "安", "危", "成", "壊", "友", "親",  # 三九
    ]

    SANKU_GROUP_NAMES = {
        1: {"name": "一九（命行）", "reading": "いっく（めいぎょう）", "head": "命"},
        2: {"name": "二九（業行）", "reading": "にく（ごうぎょう）", "head": "業"},
        3: {"name": "三九（胎行）", "reading": "さんく（たいぎょう）", "head": "胎"},
    }

    # 原典經文對照（T21n1299 卷下 各日吉凶詳述 p.397c-398a）
    CLASSICAL_POSITION_TEXTS = {
        "命": {
            "sutra": "命宿日、胎宿日，不宜舉動百事。",
            "ref": "T21, p.397c",
            "interpretation": "命宿是本命位置，對方落在此處代表你們如鏡相照，根源相同。經文說命日不宜妄動，暗示這段關係中雙方容易彼此牽制，需以觀照取代衝動。",
        },
        "業": {
            "sutra": "值業宿日，所作善惡亦不成就，甚衰。（品三另記：業宿直日，所作皆吉祥）",
            "ref": "T21, p.397c; 品三 p.391b",
            "interpretation": "業宿代表過去累積的因果。對方落在此位，彼此有深厚的業力牽連。卷下直言業日做事難成，但品三卻記載「所作皆吉祥」，兩處記載矛盾（系統從卷下）。提醒這段關係中不宜急躁推進，順其自然比強求更好。",
        },
        "胎": {
            "sutra": "命宿日、胎宿日，不宜舉動百事。",
            "ref": "T21, p.397c",
            "interpretation": "胎宿代表未來的可能性，帶有來世延續的因緣。與命宿同樣不宜妄動，但胎含孕育之意，靜待時機成熟方可行動。",
        },
        "栄": {
            "sutra": "若榮宿日，即宜入官拜職、對見大人、上書表進獻君王、興營買賣、裁著新衣、沐浴及諸吉事並大吉。出家人剃髮、割爪甲、沐浴、承事師主、啟請法要並吉。",
            "ref": "T21, p.397c-398a",
            "interpretation": "栄宿是繁榮興旺之位。對方落在你的栄位，代表此人帶給你好運和提升的能量。經文列舉入官拜職、買賣等諸多吉事，出家人亦記剃髮、承事師主、啟請法要並吉，是最適合積極行動的位置。",
        },
        "衰": {
            "sutra": "若衰日，唯宜解除諸惡、療病。（品三另記：衰、危、壞宿日，並不宜遠行，出入遷移、買賣裁衣、剃頭剪甲並不吉）",
            "ref": "T21, p.398a; 品三 p.391b",
            "interpretation": "衰宿主療癒與消退。對方落在你的衰位，此人在你的生命中扮演療癒者的角色——幫你排除負面、治療傷痛。卷下用「唯宜」二字限定療癒淨化之用，品三另記遠行、遷移、買賣等皆不吉，提醒此關係中不宜積極推展外務。",
        },
        "安": {
            "sutra": "若安宿日，移徙吉，遠行人入宅、造作園宅、安坐臥床帳、作壇場並吉。",
            "ref": "T21, p.397c-398a",
            "interpretation": "安宿主穩定和安居。對方落在你的安位，代表此人帶給你安定感。經文提到遷居、造宅等安頓之事皆吉，這段關係有穩固根基的作用。",
        },
        "危": {
            "sutra": "若危宿日，宜結交、定婚姻，歡宴聚會並吉。（另記：若危壞日，並不宜遠行出、入移徙、買賣、婚姻、裁衣、剃頭、沐浴並凶）",
            "ref": "T21, p.397c-398a",
            "interpretation": "危宿兼具吉凶兩面。卷下獨立記載危日「宜結交、定婚姻」（T21 p.397c-398a），但與壊日合述時又列婚姻為凶，經文自身存在矛盾。一般詮釋為危日的社交面為吉、遷移買賣等外務為凶。對方落在你的危位，互動中需區分社交與實務。",
        },
        "成": {
            "sutra": "若成宿日，宜修道學問、合和長年藥法，作諸成就法並吉。",
            "ref": "T21, p.398a",
            "interpretation": "成宿主成就和學習。對方落在你的成位，代表此人是你借力成事的對象。經文提到修道學問、合藥成就，這段關係適合在專業領域互相切磋、共同精進。",
        },
        "壊": {
            "sutra": "若壞日，宜作鎮壓、降伏怨讎及討伐阻壞奸惡之謀，餘並不堪。",
            "ref": "T21, p.398a",
            "interpretation": "壊宿主破壞和降伏。對方落在你的壊位，代表此人會打破你的既有模式。經文指出壊日只適合鎮壓降伏，「餘並不堪」四字表明這股力量是一次性的，衝擊過後便歸於平靜。",
        },
        "友": {
            "sutra": "若友宿日、親宿日，宜結交、定婚姻，歡宴聚會並吉。",
            "ref": "T21, p.397c-398a",
            "interpretation": "友宿主交誼和給予。對方落在你的友位，你是這段關係中主動付出的一方。經文明確指出友日適合結交和婚姻，是社交吉位。",
        },
        "親": {
            "sutra": "若友宿日、親宿日，宜結交、定婚姻，歡宴聚會並吉。",
            "ref": "T21, p.397c-398a",
            "interpretation": "親宿主親近和吸引。對方落在你的親位，代表此人自然被你吸引。與友宿共用經文，同為社交吉位，差別在於親是接受方、友是給予方。",
        },
    }

    # === 原典→職場 逐條對照表（Canonical Source，所有模組共用） ===
    # 基於 T21n1299 各日吉凶經文，每條原典對應一句現代職場建議
    # sutra_career: (經文, 現代詮釋, CBETA頁碼)
    CBETA_BASE = "https://cbetaonline.dila.edu.tw/zh/T21n1299_p"

    # === 原典→職場 結構化指引（三段式：適合/時機不佳/對治） ===
    # guidance.suitable: 原典明確說吉的行為
    # guidance.timing_poor: 原典說時機不佳的行為（事倍功半，非禁止）
    # guidance.remedy: 對治建議（如何順應能量流向）
    # sutra_career / summary / action_advice: 向下相容保留
    CAREER_CANONICAL_MAP = {
        "命": {
            "guidance": {
                "suitable": [
                    {"sutra": "宜修功德（品三凌犯化解）", "cbeta": "0391b",
                     "seeker": "充實自己：考證照、上課、整理作品集、盤點實力",
                     "hr": "可安排內訓或進修的職位（教育訓練、知識管理、內部稽核）"},
                ],
                "timing_poor": [
                    {"sutra": "不宜舉動百事", "cbeta": "0397c",
                     "seeker": "主動爭取升遷、跳槽、談薪 — 投入多回報少，等待更好時機",
                     "hr": "主動委以開創性新任務的時機偏差，安排在既有職責範圍內"},
                ],
                "remedy": {
                    "principle": "宜靜不宜動，向內充實",
                    "seeker": "現在不是出擊的時候，但正是累積彈藥的好時機。考證照、整理作品集、學新技術，這些投資會在下一個栄方或安方時派上用場。",
                    "hr": "安排在穩定型職位（行政助理、文書處理、資料維護），搭配內訓充電計畫。此人在熟悉的領域能穩定產出。",
                },
            },
            "sutra_career": [
                ("不宜舉動百事", "等待更好時機：把精力放在充實自己而非主動出擊", "維持現有職責的穩定型職位（行政助理、文書處理、資料維護）", "0397c"),
                ("宜修功德（品三凌犯化解）", "利用等待期充實自己：考證照、上課、整理作品集", "可安排內訓或進修的職位（教育訓練、知識管理、內部稽核）", "0391b"),
            ],
            "summary": "適合穩定型職位，在熟悉的領域穩定產出，搭配內訓充電計畫",
            "action_advice": "把精力放在充實自己，為下一波行動做準備",
        },
        "栄": {
            "guidance": {
                "suitable": [
                    {"sutra": "宜入官拜職", "cbeta": "0397c",
                     "seeker": "主動爭取升遷、面試時展現領導力",
                     "hr": "適合升遷或委以要職（部門主管、專案負責人、技術主管）"},
                    {"sutra": "對見大人", "cbeta": "0397c",
                     "seeker": "約面試官或高層一對一面談，展現你的視野和格局",
                     "hr": "適合需要向上溝通的職位（幕僚、特助、策略規劃）"},
                    {"sutra": "上書表進獻君王", "cbeta": "0397c",
                     "seeker": "準備完整企劃書或作品集，展現提案能力",
                     "hr": "適合企劃提案型工作（行銷企劃、產品經理、提案顧問）"},
                    {"sutra": "興營買賣", "cbeta": "0397c",
                     "seeker": "面試時強調業績和開發新客戶的經驗",
                     "hr": "適合業務開發職位（業務主管、客戶經理、事業拓展）"},
                ],
                "timing_poor": [],
                "remedy": {
                    "principle": "積極行動，時機正好",
                    "seeker": "這是最好的出手時機。升遷、提案、面試、開拓新客戶，行動都會有超出預期的回報。準備好就衝。",
                    "hr": "此人正處活躍期，給予發揮空間和資源，能帶來超出預期的貢獻。適合委以核心職務。",
                },
            },
            "sutra_career": [
                ("宜入官拜職", "面試時展現領導力，主動爭取主管職或負責人角色", "適合升遷或委以要職（部門主管、專案負責人、技術主管）", "0397c"),
                ("對見大人", "約面試官或高層一對一面談，展現你的視野", "適合需要向上溝通的職位（幕僚、特助、策略規劃）", "0397c"),
                ("上書表進獻君王", "準備完整企劃書或作品集帶去面試，展現提案能力", "適合企劃提案型工作（行銷企劃、產品經理、提案顧問）", "0397c"),
                ("興營買賣", "面試時強調你的業績和開發新客戶的經驗", "適合業務開發職位（業務主管、客戶經理、事業拓展）", "0397c"),
            ],
            "summary": "積極行動的好時機，升遷、提案、業務開拓都會有回報",
            "action_advice": "面試時積極展現自己，爭取升遷拓展的機會",
        },
        "衰": {
            "guidance": {
                "suitable": [
                    {"sutra": "唯宜解除諸惡、療病", "cbeta": "0398a",
                     "seeker": "解決既有問題、排除障礙、品質把關、除錯修復",
                     "hr": "問題排除型職位（維修工程師、品管檢測、客訴處理）"},
                    {"sutra": "宜修功德（品三）", "cbeta": "0391b",
                     "seeker": "考證照、進修、整理作品集、學新技術",
                     "hr": "可安排內訓或進修的職位（教育訓練、知識管理）"},
                ],
                "timing_poor": [
                    {"sutra": "不宜出入遷移", "cbeta": "0391b",
                     "seeker": "跳槽、轉職、搬遷 — 容易水土不服，投入多回報少",
                     "hr": "頻繁調動此人效果不佳，讓其在固定據點深耕"},
                    {"sutra": "不宜買賣", "cbeta": "0391b",
                     "seeker": "接案、談合約、對外報價 — 容易破局或被殺價",
                     "hr": "對外採購或合約談判的成效有限，安排內部執行型工作"},
                ],
                "remedy": {
                    "principle": "向內充實，累積下一波的資本",
                    "seeker": "把精力從「向外擴張」轉到「向內充實」。接案談約現在時機不對，但考證照、學新技術正是好時候。現在累積的實力會在下一個栄方或安方時派上用場。",
                    "hr": "安排在問題排除或品質把關的職位，搭配內訓計畫。此人擅長解決既有問題，在固定據點能持續發揮。",
                },
            },
            "sutra_career": [
                ("唯宜解除諸惡、療病", "面試時強調你解決問題的經驗，選有明確痛點的職位", "適合問題排除型職位（維修工程師、客訴處理、品管檢測）", "0398a"),
                ("不宜出入遷移", "選擇穩定、固定據點的職位，專注在同一間公司深耕", "適合固定據點的穩定型職位（駐廠工程師、在地服務、門市管理）", "0391b"),
                ("不宜買賣", "選內部執行型工作，把精力放在本職", "適合內部執行型工作（生產管理、倉儲物流、內部系統維運）", "0391b"),
            ],
            "summary": "擅長解決既有問題，適合穩定執行型工作，搭配進修計畫能持續成長",
            "action_advice": "專心解決手頭問題，搭配考照進修累積實力",
        },
        "安": {
            "guidance": {
                "suitable": [
                    {"sutra": "移徙吉", "cbeta": "0397c",
                     "seeker": "選正在拓展新據點的公司，新事業體或分公司優先",
                     "hr": "新事業體籌備、據點設立、分公司開設"},
                    {"sutra": "遠行人入宅", "cbeta": "0397c",
                     "seeker": "適合有出差但有固定基地的工作，出差歸來能快速上手",
                     "hr": "需要出差但有固定基地的職位（區域業務、巡迴技師、駐點顧問）"},
                    {"sutra": "造作園宅", "cbeta": "0397c",
                     "seeker": "選正在建設新團隊或新部門的公司，你能幫它從零建起",
                     "hr": "新部門建設、環境規劃型工作（廠務規劃、空間設計、設備導入）"},
                    {"sutra": "作壇場並吉", "cbeta": "0397c",
                     "seeker": "選正在導入新制度的公司，面試時強調流程建立的經驗",
                     "hr": "制度建立、流程規劃型職位（ISO 推動、SOP 撰寫、合規管理）"},
                ],
                "timing_poor": [],
                "remedy": {
                    "principle": "安頓扎根，建立穩固基礎",
                    "seeker": "這是建立根基的好時機。搬遷、轉調、加入新團隊都順利。選正在擴張的公司，你的安頓能力正是他們需要的。",
                    "hr": "此人適合長期培養，入職後能快速融入環境。安排在需要建立新據點或新制度的職位最能發揮。",
                },
            },
            "sutra_career": [
                ("移徙吉", "適合選正在拓展新據點的公司，新事業體或分公司優先", "適合新事業體籌備、據點設立、分公司開設等需要從無到有建立的職位", "0397c"),
                ("遠行人入宅", "適合有出差但有固定基地的工作，出差歸來能快速上手", "需要出差但有固定基地的職位（區域業務、巡迴技師、駐點顧問）", "0397c"),
                ("造作園宅", "適合選正在建設新團隊或新部門的公司，你能幫它從零建起", "新部門建設、環境規劃型工作（廠務規劃、空間設計、設備導入）", "0397c"),
                ("作壇場並吉", "適合選正在導入新制度的公司，面試時強調流程建立的經驗", "制度建立、流程規劃型職位（ISO 推動、SOP 撰寫、合規管理）", "0397c"),
            ],
            "summary": "適合安頓新環境、建立穩固據點，在需要從無到有建立的工作中最能發揮",
            "action_advice": "適合安頓下來長期發展，建立穩固的工作據點",
        },
        "危": {
            "guidance": {
                "suitable": [
                    {"sutra": "宜結交、歡宴聚會並吉", "cbeta": "0397c",
                     "seeker": "社交聚會、團隊經營、拓展公司內部人脈",
                     "hr": "對外聯繫、社交型職位（公關、客戶關係、社群經營、活動企劃）"},
                ],
                "timing_poor": [
                    {"sutra": "不宜遠行出入移徙", "cbeta": "0398a",
                     "seeker": "頻繁出差、外派、職務調動 — 移動中容易出狀況",
                     "hr": "頻繁派此人出差效果不佳，安排在公司內部發揮社交長才"},
                    {"sutra": "不宜買賣", "cbeta": "0391b",
                     "seeker": "大筆合約談判、重大採購 — 交易過程容易卡關",
                     "hr": "大筆合約談判成效有限，安排在日常營運型工作"},
                ],
                "remedy": {
                    "principle": "社交力用在內部，暫緩對外擴張",
                    "seeker": "你的社交能力是強項，但現在適合把它用在公司內部 — 經營團隊關係、參加部門聚餐、建立跨部門人脈。對外的大筆交易暫緩。",
                    "hr": "此人社交能力突出，安排在需要內部協調或團隊經營的職位。對外談判的時機稍差，暫由他人負責。",
                },
            },
            "sutra_career": [
                ("宜結交、歡宴聚會並吉", "選重視團隊氛圍的公司，面試時展現社交力和協調能力", "適合對外聯繫、社交型職位（公關、客戶關係、社群經營、活動企劃）", "0397c"),
                ("不宜遠行出入移徙", "選公司內部的駐點型工作，在熟悉環境中發揮社交長才", "適合公司內部的駐點型工作（辦公室行政、內勤企劃、現場管理）", "0398a"),
                ("不宜買賣", "把社交能力用在團隊經營，合約談判的時機稍差", "適合日常營運型工作（庶務管理、排程調度、客服支援）", "0391b"),
            ],
            "summary": "社交應酬是強項，適合在公司內部發揮協調和團隊經營能力",
            "action_advice": "面試時展現社交力，入職後經營團隊關係",
        },
        "成": {
            "guidance": {
                "suitable": [
                    {"sutra": "宜修道學問", "cbeta": "0398a",
                     "seeker": "學習進修、考證照、參加研討會",
                     "hr": "需持續學習的職位（研發工程師、資料分析師、技術顧問）"},
                    {"sutra": "合和長年藥法", "cbeta": "0398a",
                     "seeker": "長期研發專案、持續深耕技術",
                     "hr": "長期研發專案（產品研發、製程改善、技術架構設計）"},
                    {"sutra": "作諸成就法並吉", "cbeta": "0398a",
                     "seeker": "完成專案交付、達成目標，努力會有具體成果",
                     "hr": "專案交付型職位（專案經理、系統整合、導入顧問）"},
                ],
                "timing_poor": [],
                "remedy": {
                    "principle": "深耕學習，努力會有成果",
                    "seeker": "學習和交付都是順風的。選有完善教育訓練制度的公司，你能在裡面持續成長。面試時強調學習力和專案達標紀錄。",
                    "hr": "此人學習力強，提供進修和考照機會能快速提升戰力。委以專案能如期完成。",
                },
            },
            "sutra_career": [
                ("宜修道學問", "選有完善教育訓練制度的公司，面試時強調學習力和證照", "適合需持續學習的職位（研發工程師、資料分析師、技術顧問）", "0398a"),
                ("合和長年藥法", "選有長期研發專案的公司，你能在裡面持續深耕出成果", "適合長期研發專案（產品研發、製程改善、技術架構設計）", "0398a"),
                ("作諸成就法並吉", "面試時展現你的專案交付經驗和達標紀錄", "適合專案交付型職位（專案經理、系統整合、導入顧問）", "0398a"),
            ],
            "summary": "學習進修和專案交付都是順風，努力會有具體成果",
            "action_advice": "面試時強調學習力和專業能力，入職後適合進修",
        },
        "壊": {
            "guidance": {
                "suitable": [
                    {"sutra": "宜作鎮壓、降伏怨讎", "cbeta": "0398a",
                     "seeker": "處理棘手問題、危機應變、排除障礙",
                     "hr": "危機處理型職位（法務、風控、資安應變、客訴升級處理）"},
                ],
                "timing_poor": [
                    {"sutra": "餘並不堪", "cbeta": "0398a",
                     "seeker": "日常例行事務 — 容易覺得無聊或表現平平，精力該聚焦在難題上",
                     "hr": "例行行政或日常事務效果有限，聚焦在疑難排解型任務"},
                ],
                "remedy": {
                    "principle": "聚焦困難任務，其餘交由他人",
                    "seeker": "你在解決難題時最能發揮。選有棘手問題需要處理的公司，面試時展現抗壓和排除障礙的能力。例行事務不是你的主場。",
                    "hr": "此人適合處理困難任務和危機應變。給予明確目標能全力以赴，例行事務可交由他人分擔。搭配 3-6 個月適應期效果更佳。",
                },
            },
            "sutra_career": [
                ("宜作鎮壓、降伏怨讎", "選有棘手問題的公司，面試時展現抗壓和排除障礙能力", "適合危機處理型職位（法務、風控、資安應變、客訴升級處理）", "0398a"),
                ("餘並不堪", "選有挑戰性的工作，你在解決難題時最能發揮", "聚焦在疑難排解型任務最能發揮，例行事務可交由他人分擔", "0398a"),
            ],
            "summary": "擅長處理棘手問題和危機應變，在有挑戰的環境中最能發揮",
            "action_advice": "入職後聚焦在疑難排解型任務，這是你的主場",
        },
        "友": {
            "guidance": {
                "suitable": [
                    {"sutra": "宜結交朋友大吉", "cbeta": "0391b",
                     "seeker": "拓展人脈、參加業界活動和社群聚會",
                     "hr": "需要人脈經營的職位（業務開發、異業合作、社群營運）"},
                    {"sutra": "歡宴聚會並吉", "cbeta": "0397c",
                     "seeker": "團隊建設、社交聚餐，人脈會帶來工作機會",
                     "hr": "團隊協作型職位（HR 人資、團隊 lead、跨部門協調）"},
                ],
                "timing_poor": [],
                "remedy": {
                    "principle": "社交帶來機會，多參加活動",
                    "seeker": "人脈就是你現在最大的資產。多參加業界活動、社群聚會，工作機會會從人際網路中冒出來。選重視團隊合作的公司。",
                    "hr": "此人團隊合作能力佳，能為部門帶來外部人脈資源和正向氛圍。適合需要協作和跨部門溝通的職位。",
                },
            },
            "sutra_career": [
                ("宜結交朋友大吉", "多參加業界活動和社群聚會，人脈會帶來工作機會", "適合需要人脈經營的職位（業務開發、異業合作、社群營運）", "0391b"),
                ("歡宴聚會並吉", "選重視團隊合作的公司，面試時展現協作和帶動氣氛的能力", "適合團隊協作型職位（HR 人資、團隊 lead、跨部門協調）", "0397c"),
            ],
            "summary": "社交帶來機會，拓展人脈和團隊建設都是順風",
            "action_advice": "入職後積極拓展人脈、建立團隊關係",
        },
        "親": {
            "guidance": {
                "suitable": [
                    {"sutra": "宜結交", "cbeta": "0397c",
                     "seeker": "接受公司資源與栽培，選願意培養新人的公司",
                     "hr": "接受培訓的儲備職位（MA 儲備幹部、內部輪調、接班梯隊）"},
                    {"sutra": "定婚姻", "cbeta": "0397c",
                     "seeker": "談長期合約、表達穩定意願和長期規劃",
                     "hr": "簽長約的長聘職位（核心研發、資深顧問、合夥人）"},
                    {"sutra": "歡宴聚會並吉", "cbeta": "0397c",
                     "seeker": "面試時展現社交禮儀和對外應對能力",
                     "hr": "對外代表公司的職位（公關發言人、商務代表、VIP 接待）"},
                ],
                "timing_poor": [],
                "remedy": {
                    "principle": "深化合作，接受栽培",
                    "seeker": "公司願意給你資源和栽培的機會，接受它。適合談長期合作、簽正式合約。面試氣氛會比較輕鬆，對方對你印象好。",
                    "hr": "此人與公司契合度高，忠誠度強。值得長期投資培養，給予公司資源和栽培機會能深化合作關係。",
                },
            },
            "sutra_career": [
                ("宜結交", "選願意栽培新人的公司，面試時表達你願意長期投入", "適合接受培訓的儲備職位（MA 儲備幹部、內部輪調、接班梯隊）", "0397c"),
                ("定婚姻", "適合談長期合約，面試時表達穩定意願和長期規劃", "適合簽長約的長聘職位（核心研發、資深顧問、合夥人）", "0397c"),
                ("歡宴聚會並吉", "面試時展現社交禮儀和對外應對能力", "適合對外代表公司的職位（公關發言人、商務代表、VIP 接待）", "0397c"),
            ],
            "summary": "與公司契合度高，適合接受栽培和長期合作",
            "action_advice": "接受公司給的資源與栽培，深化合作關係",
        },
        "業": {
            "guidance": {
                "suitable": [
                    {"sutra": "宜修功德（品三）", "cbeta": "0391b",
                     "seeker": "學習充電、研究調查、整理知識庫",
                     "hr": "研究調查或知識建置的職位（研究員、資料建檔、系統維護）"},
                ],
                "timing_poor": [
                    {"sutra": "所作善惡亦不成就", "cbeta": "0397c",
                     "seeker": "績效導向型工作 — 短期內投入和產出不成正比，非能力問題而是時運",
                     "hr": "短期績效型職位（業務目標、KPI 考核）成效有限，安排在長期累積型工作"},
                    {"sutra": "甚衰", "cbeta": "0397c",
                     "seeker": "主動出擊、大動作 — 能量處於蓄積期，行動效果打折",
                     "hr": "需要立即產出成果的職位效果打折，安排在幕後支援型工作"},
                ],
                "remedy": {
                    "principle": "蓄積能量，為下一個高峰做準備",
                    "seeker": "現在是能量蓄積期，做什麼都像逆風跑。最聰明的做法是把精力放在學習充電和累積實力上，等能量回升時你會比別人準備得更充分。",
                    "hr": "此人適合長期累積型工作，在低壓環境中蓄積能量。安排在研究調查或知識建置的職位，給予充足成長時間，著眼長期發展。",
                },
            },
            "sutra_career": [
                ("所作善惡亦不成就", "選能慢慢累積的工作，在穩定環境中蓄積能量", "適合長期累積型工作（研究調查、資料建檔、知識庫建置），給予充足的成長時間", "0397c"),
                ("甚衰", "選幕後支援型工作，在穩定環境中蓄積能量，為下一波行動做準備", "適合幕後支援型職位（後勤支援、文件整理、系統維護），讓此人在低壓環境蓄積能量", "0397c"),
            ],
            "summary": "適合長期累積型工作，在穩定環境中蓄積能量，為下一個高峰做準備",
            "action_advice": "把精力放在學習充電和累積實力上",
        },
        "胎": {
            "guidance": {
                "suitable": [
                    {"sutra": "宜修功德（品三凌犯化解）", "cbeta": "0391b",
                     "seeker": "選有培訓制度的公司，當作累積實力的跳板",
                     "hr": "儲備培養型職位（實習轉正、學徒制、長期培訓計畫）"},
                ],
                "timing_poor": [
                    {"sutra": "不宜舉動百事（同命日）", "cbeta": "0397c",
                     "seeker": "從零開始的開創型工作 — 時機未到，在成熟體系中穩定發展更順",
                     "hr": "開創型職位（新事業開發、創業專案）時機稍差，安排在既有業務"},
                ],
                "remedy": {
                    "principle": "在成熟體系中穩定發展",
                    "seeker": "選有既有基礎可以接手的工作，在成熟的體系中穩定發展。你是潛力型，時機成熟時會有突破。現在的累積都不會白費。",
                    "hr": "此人潛力型，長期培養可期。適合接手既有業務穩定發展，給予成長空間和時間。",
                },
            },
            "sutra_career": [
                ("不宜舉動百事（同命日）", "選有既有基礎可接手的工作，在成熟體系中穩定發展", "適合接手既有業務的職位（現有產線維運、既有客戶維護、成熟團隊成員）", "0397c"),
                ("宜修功德（品三凌犯化解）", "選有培訓制度的公司，當作累積實力的跳板", "適合儲備培養型職位（實習轉正、學徒制、長期培訓計畫）", "0391b"),
            ],
            "summary": "潛力型，適合接手既有業務穩定發展，時機成熟時會有突破",
            "action_advice": "在成熟體系中累積實力，為未來的突破做準備",
        },
    }

    # === HR 模式：原典→公司選才 視角（公司看候選人） ===
    # 基於同一組原典經文，但從「公司評估候選人」的角度詮釋
    HR_CANONICAL_MAP = {
        "命": {
            "summary": "此人適合穩定型職位，在熟悉的領域能穩定產出，給予內訓機會可進一步提升",
            "action_advice": "安排穩定執行型工作，搭配內訓充電計畫",
        },
        "栄": {
            "summary": "此人正處活躍期，能為團隊帶來活力，適合需要積極開拓的職位",
            "action_advice": "給予發揮空間和資源，能帶來超出預期的貢獻",
        },
        "衰": {
            "summary": "此人擅長解決既有問題，適合穩定執行型工作，在固定據點能持續發揮",
            "action_advice": "安排在問題排除或品質把關的職位，穩定中見長",
        },
        "安": {
            "summary": "此人適合長期培養，入職後能快速融入環境，適合建立穩固的工作據點",
            "action_advice": "適合長聘培養型人才，安排穩定的部門發展",
        },
        "危": {
            "summary": "此人社交能力強，適合面對客戶或需要協調的職位，在團隊互動中表現突出",
            "action_advice": "安排在需要對外溝通的職位，社交場合是其強項",
        },
        "成": {
            "summary": "此人學習力強，適合需要持續成長和專案交付的職位，努力會有成果",
            "action_advice": "提供進修和考照機會，能快速提升戰力",
        },
        "壊": {
            "summary": "此人適合處理困難任務和危機應變，給予明確目標能全力以赴",
            "action_advice": "安排在疑難排解型職位，搭配 3-6 個月適應期效果更佳",
        },
        "友": {
            "summary": "此人團隊合作能力佳，適合協作型職位，社交能帶來正向影響",
            "action_advice": "安排在需要團隊協作的部門，能促進團隊氛圍",
        },
        "親": {
            "summary": "此人與公司契合度高，適合接受培訓栽培，深化合作關係",
            "action_advice": "值得長期投資培養，給予公司資源和栽培機會",
        },
        "業": {
            "summary": "此人適合長期累積型工作，在低壓環境中能穩定蓄積能量，著眼長期發展",
            "action_advice": "安排在研究調查或知識建置的職位，給予充足成長時間",
        },
        "胎": {
            "summary": "此人潛力型，適合接手既有業務穩定發展，長期培養可期",
            "action_advice": "適合儲備人才計畫，給予成長空間和時間",
        },
    }

    @classmethod
    def get_hr_summary(cls, direction: str) -> str:
        """從 HR_CANONICAL_MAP 取得公司選才視角的一句話總結"""
        entry = cls.HR_CANONICAL_MAP.get(direction)
        return entry["summary"] if entry else ""

    @classmethod
    def get_hr_action_advice(cls, direction: str) -> str:
        """從 HR_CANONICAL_MAP 取得公司選才視角的行動建議"""
        entry = cls.HR_CANONICAL_MAP.get(direction)
        return entry["action_advice"] if entry else ""

    _guidance_cache: dict = {}

    @classmethod
    def _load_guidance_json(cls, lang: str) -> dict:
        """載入 guidance JSON 字典檔（有快取）"""
        if lang in cls._guidance_cache:
            return cls._guidance_cache[lang]
        import json
        from pathlib import Path
        json_path = Path(__file__).parent.parent / "data" / "i18n" / lang / "guidance.json"
        if json_path.exists():
            with open(json_path, encoding="utf-8") as f:
                cls._guidance_cache[lang] = json.load(f)
                return cls._guidance_cache[lang]
        return {}

    @classmethod
    def get_direction_guidance(cls, direction: str, mode: str = "seeker", lang: str = "zh-TW") -> dict:
        """取得結構化方向指引（適合/時機不佳/對治），支援多語系"""
        # 優先從 JSON 字典檔讀取
        json_data = cls._load_guidance_json(lang)
        dir_data = json_data.get("directions", {}).get(direction)

        if dir_data:
            perspective = "hr" if mode == "hr" else "seeker"
            suitable = []
            for item in dir_data.get("suitable", []):
                cbeta = item.get("cbeta", "")
                suitable.append({
                    "sutra": item["sutra"],
                    "cbeta_url": f"{cls.CBETA_BASE}{cbeta}" if cbeta else "",
                    "interpretation": item.get(perspective, ""),
                })
            timing_poor = []
            for item in dir_data.get("timing_poor", []):
                cbeta = item.get("cbeta", "")
                timing_poor.append({
                    "sutra": item["sutra"],
                    "cbeta_url": f"{cls.CBETA_BASE}{cbeta}" if cbeta else "",
                    "interpretation": item.get(perspective, ""),
                })
            remedy_data = dir_data.get("remedy", {})
            remedy = {
                "principle": remedy_data.get("principle", ""),
                "detail": remedy_data.get(perspective, ""),
            }
            return {"suitable": suitable, "timing_poor": timing_poor, "remedy": remedy}

        # Fallback: 從硬編碼的 CAREER_CANONICAL_MAP 讀取（zh-TW）
        entry = cls.CAREER_CANONICAL_MAP.get(direction)
        if not entry or "guidance" not in entry:
            return {"suitable": [], "timing_poor": [], "remedy": {}}

        g = entry["guidance"]
        perspective = "hr" if mode == "hr" else "seeker"

        suitable = []
        for item in g.get("suitable", []):
            cbeta = item.get("cbeta", "")
            suitable.append({
                "sutra": item["sutra"],
                "cbeta_url": f"{cls.CBETA_BASE}{cbeta}" if cbeta else "",
                "interpretation": item[perspective],
            })
        timing_poor = []
        for item in g.get("timing_poor", []):
            cbeta = item.get("cbeta", "")
            timing_poor.append({
                "sutra": item["sutra"],
                "cbeta_url": f"{cls.CBETA_BASE}{cbeta}" if cbeta else "",
                "interpretation": item[perspective],
            })
        remedy_data = g.get("remedy", {})
        remedy = {
            "principle": remedy_data.get("principle", ""),
            "detail": remedy_data.get(perspective, ""),
        }
        return {"suitable": suitable, "timing_poor": timing_poor, "remedy": remedy}

    @classmethod
    def get_direction_desc(cls, direction: str) -> str:
        """從 canonical map 產生逐條對照描述（原典→現代職場）"""
        entry = cls.CAREER_CANONICAL_MAP.get(direction)
        if not entry:
            return ""
        parts = [f"原典「{item[0]}」→ {item[1]}" for item in entry["sutra_career"]]
        return "\n".join(parts)

    @classmethod
    def get_sutra_career_items(cls, direction: str) -> list[dict]:
        """回傳結構化的原典逐條資料（求職者視角，含 CBETA 超連結），供前端渲染"""
        entry = cls.CAREER_CANONICAL_MAP.get(direction)
        if not entry:
            return []
        items = []
        for item in entry["sutra_career"]:
            sutra, interpretation = item[0], item[1]
            # 新格式: (經文, 求職者詮釋, HR詮釋, CBETA頁碼)
            page = item[3] if len(item) > 3 else (item[2] if len(item) > 2 and not item[2].startswith("此") else "")
            cbeta_url = f"{cls.CBETA_BASE}{page}" if page else ""
            items.append({
                "sutra": sutra,
                "interpretation": interpretation,
                "cbeta_url": cbeta_url,
            })
        return items

    @classmethod
    def get_hr_sutra_career_items(cls, direction: str) -> list[dict]:
        """回傳結構化的原典逐條資料（HR 視角：公司看候選人），供前端渲染"""
        entry = cls.CAREER_CANONICAL_MAP.get(direction)
        if not entry:
            return []
        items = []
        for item in entry["sutra_career"]:
            sutra = item[0]
            hr_interpretation = item[2] if len(item) > 3 else item[1]
            page = item[3] if len(item) > 3 else (item[2] if len(item) > 2 else "")
            cbeta_url = f"{cls.CBETA_BASE}{page}" if page else ""
            items.append({
                "sutra": sutra,
                "interpretation": hr_interpretation,
                "cbeta_url": cbeta_url,
            })
        return items

    @classmethod
    def get_career_summary(cls, direction: str, lang: str = "zh-TW") -> str:
        """從 JSON 或 canonical map 取得職場一句話總結"""
        json_data = cls._load_guidance_json(lang)
        dir_data = json_data.get("directions", {}).get(direction, {})
        if dir_data.get("summary"):
            return dir_data["summary"]
        entry = cls.CAREER_CANONICAL_MAP.get(direction)
        return entry["summary"] if entry else ""

    @classmethod
    def get_action_advice(cls, direction: str, lang: str = "zh-TW") -> str:
        """從 JSON 或 canonical map 取得投遞/面試建議"""
        json_data = cls._load_guidance_json(lang)
        dir_data = json_data.get("directions", {}).get(direction, {})
        if dir_data.get("action_advice"):
            return dir_data["action_advice"]
        entry = cls.CAREER_CANONICAL_MAP.get(direction)
        return entry["action_advice"] if entry else ""

    @classmethod
    def _build_career_with_sutra(cls, rel_type: str, career_advice: str) -> str:
        """從 canonical map 動態組裝原典引文前綴 + 距離建議"""
        directions = cls.RELATION_DIRECTIONS.get(rel_type, ())
        if not directions:
            return career_advice
        parts = []
        for d in directions:
            entry = cls.CAREER_CANONICAL_MAP.get(d)
            if entry:
                quotes = "、".join(item[0] for item in entry["sutra_career"])
                parts.append(f"{d}位「{quotes}」")
        prefix = "原典記載" + "，".join(parts) + "。" if parts else ""
        return prefix + career_advice

    # 三九秘法位置 → 現代行動建議（職場/人際實用化）
    # career 欄位引用 CAREER_CANONICAL_MAP.summary + CLASSICAL_POSITION_TEXTS.ref
    PRACTICAL_ACTION_MAP = {
        "命": {
            "do": ["深入自我觀察", "與對方互相映照優缺點"],
            "avoid": ["衝動行事", "在關係中強求主導"],
        },
        "栄": {
            "do": ["積極爭取合作機會", "借力拓展事業版圖", "把握對方帶來的資源"],
            "avoid": ["錯過黃金時機", "對好運視而不見"],
        },
        "衰": {
            "do": ["專心解決手頭的問題", "處理累積的待辦事項"],
            "avoid": ["跳槽或轉換跑道", "發展副業、外包、接案"],
        },
        "安": {
            "do": ["安頓工作環境", "推進需要穩定基礎的事務", "建立長期據點"],
            "avoid": ["急於求成", "忽略細節和根基"],
        },
        "危": {
            "do": ["參加聚會、拓展社交", "經營人際關係"],
            "avoid": ["出差或遠行", "大筆交易或採購"],
        },
        "成": {
            "do": ["學習進修", "考取證照", "完成重要專案"],
            "avoid": ["只談不做", "忽略成果驗收"],
        },
        "壊": {
            "do": ["處理棘手問題", "對付惡意競爭或不合理的狀況"],
            "avoid": ["發展新業務", "期望一切照常運作"],
        },
        "友": {
            "do": ["拓展人脈", "參加社交活動", "團隊建設"],
            "avoid": ["只付出不設界限", "忽略自身需求"],
        },
        "親": {
            "do": ["接受對方的善意與資源", "深化既有合作", "擴大交友圈"],
            "avoid": ["被動等待", "不回應對方的好意"],
        },
        "業": {
            "do": ["低調收斂", "整理過去的經驗教訓"],
            "avoid": ["強行改變關係走向", "急躁推進"],
        },
        "胎": {
            "do": ["耐心等待時機成熟", "靜心為下一階段做準備"],
            "avoid": ["揠苗助長", "急於看到成果"],
        },
    }

    @classmethod
    def _get_practical_career(cls, direction: str) -> str:
        """從 canonical map 產生帶原典出處的 career 描述"""
        canonical = cls.CAREER_CANONICAL_MAP.get(direction, {})
        classical = cls.CLASSICAL_POSITION_TEXTS.get(direction, {})
        ref = classical.get("ref", "")
        sutra = classical.get("sutra", "")
        summary = canonical.get("summary", "")
        # 格式：原典記載「經文摘要」（出處）。現代職場總結。
        sutra_short = sutra.split("。")[0] if sutra else ""
        if sutra_short and ref:
            return f"原典記載「{sutra_short}」（{ref}）。{summary}"
        return summary

    # 方向在職場情境的深度解讀（雙視角）— 以 T21n1299 各日吉凶為底
    # energy_flow: 「原典經文」— 現代詮釋（簡短一行）
    DIRECTION_CAREER_MEANINGS = {
        "栄": {
            "energy_flow": "「宜入官拜職、對見大人」— 升遷拓展的機運",
            "as_person1": "你是被提升方，適合向上爭取、主動提案",
            "as_person2": "你是提升者，你的支持能幫對方往上走",
        },
        "親": {
            "energy_flow": "「宜結交、歡宴聚會並吉」— 給你資源與栽培",
            "as_person1": "你是被栽培方，接受對方給的機會和資源",
            "as_person2": "你是栽培者，對方會接受你的指導",
        },
        "衰": {
            "energy_flow": "「唯宜解除諸惡、療病」— 專心解決問題，不宜拓展",
            "as_person1": "你在此關係中應專注解決既有問題",
            "as_person2": "你的存在幫助對方面對累積的問題",
        },
        "友": {
            "energy_flow": "「宜結交朋友大吉」— 人脈拓展、社交吉",
            "as_person1": "你是付出方，付出會轉化為人脈和機會",
            "as_person2": "你是接受方，對方會主動幫你牽線搭橋",
        },
        "安": {
            "energy_flow": "「移徙吉、造作園宅」— 安頓扎根吉",
            "as_person1": "你從對方身上獲得穩定的發展基礎",
            "as_person2": "你是對方安頓下來的支撐",
        },
        "壊": {
            "energy_flow": "「宜作鎮壓、降伏怨讎，餘並不堪」— 只適合處理棘手問題",
            "as_person1": "你在此關係中面對挑戰，只適合解決問題",
            "as_person2": "你的存在迫使對方面對必須處理的難題",
        },
        "危": {
            "energy_flow": "「宜結交、歡宴聚會」+「不宜遠行買賣」— 社交吉但行動受限",
            "as_person1": "你適合參加聚會社交，但不宜出差或大筆交易",
            "as_person2": "你帶給對方社交機會，但不適合一起做大筆買賣",
        },
        "成": {
            "energy_flow": "「宜修道學問、作諸成就法」— 學習精進、完成目標",
            "as_person1": "你在此關係中適合學習成長、完成專案",
            "as_person2": "你幫助對方在專業上精進突破",
        },
        "命": {
            "energy_flow": "「不宜舉動百事」— 宜靜不宜動",
            "as_person1": "你與對方本質相同，適合反省而非行動",
            "as_person2": "對方與你本質相同，適合互相映照反思",
        },
        "業": {
            "energy_flow": "「所作善惡亦不成就，甚衰」— 難以成事",
            "as_person1": "你在此關係中做什麼都難有結果",
            "as_person2": "對方在你身邊也難以發揮",
        },
        "胎": {
            "energy_flow": "「不宜舉動百事」— 靜待時機成熟",
            "as_person1": "你在此關係中適合等待而非行動",
            "as_person2": "對方需要時間才能看到你的價值",
        },
    }

    # 支援的語系
    SUPPORTED_LANGS = ('zh-TW', 'ja', 'en')
    DEFAULT_LANG = 'zh-TW'

    # lang 參數 → LEVEL_NAMES / DAILY_FORTUNE_RELATION_NAMES 的 key
    LANG_KEY_MAP = {'zh-TW': 'zh', 'ja': 'ja', 'en': 'en'}

    def _lang_key(self, lang: str) -> str:
        return self.LANG_KEY_MAP.get(lang, 'zh')

    def _level_name(self, level: str, lang: str) -> str:
        return self.LEVEL_NAMES.get(level, {}).get(self._lang_key(lang), level)

    def _relation_display_name(self, rel_type: str, lang: str) -> str:
        names = self.DAILY_FORTUNE_RELATION_NAMES.get(rel_type, {})
        if isinstance(names, dict):
            return names.get(self._lang_key(lang), rel_type)
        return names  # backward compat

    # 九曜星英文 key 對應（依 KUYOU_STARS 順序）
    KUYOU_STAR_KEYS = [
        "rahula", "saturn", "mercury", "venus", "sun",
        "mars", "ketu", "moon", "jupiter"
    ]

    def __init__(self):
        self._mansions_data = None
        self._relations_data = None
        self._elements_data = None
        self._metadata = None
        self._month_mansion_table = None
        self._i18n_cache: dict[str, dict] = {}
        self._kuyou_i18n_cache: dict[str, dict] = {}
        self._strategy_i18n_cache: dict[str, dict] = {}
        self._fortune_i18n_cache: dict[str, dict] = {}
        self._relations_i18n_cache: dict[str, dict] = {}

    def _load_relations_i18n(self, lang: str) -> dict:
        """載入關係描述翻譯 JSON (有快取)"""
        if lang in self._relations_i18n_cache:
            return self._relations_i18n_cache[lang]
        if lang not in self.SUPPORTED_LANGS:
            lang = self.DEFAULT_LANG
        i18n_path = Path(__file__).parent.parent / "data" / "i18n" / lang / "relations.json"
        if not i18n_path.exists():
            i18n_path = Path(__file__).parent.parent / "data" / "i18n" / "zh-TW" / "relations.json"
        with open(i18n_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self._relations_i18n_cache[lang] = data
        return data

    _role_guidance_cache: dict | None = None

    @classmethod
    def _load_role_guidance(cls) -> dict:
        """載入原典式角色指南 (有快取)"""
        if cls._role_guidance_cache is not None:
            return cls._role_guidance_cache
        path = Path(__file__).parent.parent / "data" / "role_guidance.json"
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                cls._role_guidance_cache = json.load(f)
        else:
            cls._role_guidance_cache = {}
        return cls._role_guidance_cache

    def _get_role_guidance(self, direction: str) -> dict:
        """取得指定方向的角色指南（含原典引用）"""
        data = self._load_role_guidance()
        # direction 是中文字（栄/親/友/衰/安/壊/危/成/命/業/胎）
        # 對應 role_guidance.json 的 key 是 cite key (ei/shin/yu/sui/an/kai/ki/sei/mei/gyo/tai)
        direction_to_key = {
            "栄": "ei", "親": "shin", "友": "yu", "衰": "sui",
            "安": "an", "壊": "kai", "危": "ki", "成": "sei",
            "命": "mei", "業": "gyo", "胎": "tai",
        }
        key = direction_to_key.get(direction, "")
        section = data.get(key, {})
        cbeta_base = data.get("_cbeta_base", "https://cbetaonline.dila.edu.tw/zh/T21n1299_p")
        result: dict = {}
        # 傳出雙方 role_label
        if section.get("role_label"):
            result["_role_label"] = section["role_label"]
        # 反方向的 role_label（對方）
        inverse_dir = self.DIRECTION_INVERSE.get(direction, direction)
        inv_key = direction_to_key.get(inverse_dir, "")
        inv_section = data.get(inv_key, {})
        if inv_section.get("role_label"):
            # 把「我」換成「對方」
            result["_inverse_role_label"] = inv_section["role_label"].replace("我", "對方")
        for role in ("lover", "spouse", "friend", "colleague", "family", "parent"):
            paragraphs = section.get(role)
            if not paragraphs:
                continue
            # 補上完整 CBETA URL
            for p in paragraphs:
                if p.get("cbeta") and not p.get("cbeta_url"):
                    p["cbeta_url"] = f"{cbeta_base}{p['cbeta']}"
            result[role] = {"paragraphs": paragraphs}
        return result

    def _load_i18n(self, lang: str) -> dict:
        """載入指定語系的文案 JSON (有快取)"""
        if lang in self._i18n_cache:
            return self._i18n_cache[lang]
        # fallback 到 zh-TW
        if lang not in self.SUPPORTED_LANGS:
            lang = self.DEFAULT_LANG
        i18n_path = Path(__file__).parent.parent / "data" / "i18n" / lang / "fortunes.json"
        if not i18n_path.exists():
            # 如果日文檔不存在，fallback 到中文
            i18n_path = Path(__file__).parent.parent / "data" / "i18n" / "zh-TW" / "fortunes.json"
        with open(i18n_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self._i18n_cache[lang] = data
        return data

    def _load_kuyou_i18n(self, lang: str) -> dict:
        """載入九曜星翻譯 JSON (有快取)"""
        if lang in self._kuyou_i18n_cache:
            return self._kuyou_i18n_cache[lang]
        if lang not in self.SUPPORTED_LANGS:
            lang = self.DEFAULT_LANG
        i18n_path = Path(__file__).parent.parent / "data" / "i18n" / lang / "kuyou.json"
        if not i18n_path.exists():
            i18n_path = Path(__file__).parent.parent / "data" / "i18n" / "zh-TW" / "kuyou.json"
        with open(i18n_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self._kuyou_i18n_cache[lang] = data
        return data

    def _load_strategy_i18n(self, lang: str) -> dict:
        """載入策略模板翻譯 JSON (有快取)"""
        if lang in self._strategy_i18n_cache:
            return self._strategy_i18n_cache[lang]
        if lang not in self.SUPPORTED_LANGS:
            lang = self.DEFAULT_LANG
        i18n_path = Path(__file__).parent.parent / "data" / "i18n" / lang / "strategy.json"
        if not i18n_path.exists():
            i18n_path = Path(__file__).parent.parent / "data" / "i18n" / "zh-TW" / "strategy.json"
        with open(i18n_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self._strategy_i18n_cache[lang] = data
        return data

    def _get_text(self, lang: str, key: str, sub_key: str) -> list:
        """從 i18n 文案取得指定 key 的文案列表，fallback 到 class 屬性"""
        i18n = self._load_i18n(lang)
        data = i18n.get(key, {})
        result = data.get(sub_key)
        if result:
            return result
        # fallback 到 class 屬性 (向後相容)
        attr_name = key.upper()
        cls_data = getattr(self, attr_name, {})
        return cls_data.get(sub_key, [""])

    @staticmethod
    def _seeded_choice(seed_key: str, pool: list):
        """獨立 seed 的 random.choice，不影響外部 seed 狀態"""
        random.seed(seed_key)
        return random.choice(pool)

    def _load_data(self):
        """載入所有資料"""
        if self._mansions_data is None:
            data_path = Path(__file__).parent.parent / "data" / "sukuyodo_mansions.json"
            with open(data_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._mansions_data = data["mansions"]
                self._relations_data = data["relations"]
                self._elements_data = data.get("elements", {})
                self._metadata = data.get("metadata", {})
                self._month_mansion_table = data.get("month_mansion_table", {})

    @property
    def mansions_data(self) -> list[dict]:
        """載入 27 宿資料"""
        self._load_data()
        return self._mansions_data

    @property
    def relations_data(self) -> dict:
        """載入關係資料"""
        self._load_data()
        return self._relations_data

    @property
    def elements_data(self) -> dict:
        """載入元素資料"""
        self._load_data()
        return self._elements_data

    @property
    def metadata(self) -> dict:
        """載入元資料"""
        self._load_data()
        return self._metadata

    @property
    def month_mansion_table(self) -> dict:
        """載入傍通曆資料"""
        self._load_data()
        return self._month_mansion_table

    def solar_to_lunar(self, solar_date: date) -> tuple[int, int, int, bool]:
        """
        西曆轉農曆

        Args:
            solar_date: 西曆日期

        Returns:
            (年, 月, 日, 是否閏月)

        Raises:
            RuntimeError: 當 lunarcalendar 套件未安裝時
        """
        try:
            from lunarcalendar import Converter, Solar
            solar = Solar(solar_date.year, solar_date.month, solar_date.day)
            lunar = Converter.Solar2Lunar(solar)
            return (lunar.year, lunar.month, lunar.day, lunar.isleap)
        except ImportError:
            raise RuntimeError(
                "lunarcalendar 套件未安裝。"
                "請執行 'pip install lunarcalendar' 安裝。"
                "宿曜道計算需要精確的農曆轉換，不接受近似值。"
            )

    def lunar_to_solar(self, lunar_year: int, lunar_month: int, lunar_day: int) -> Optional[date]:
        """
        農曆轉西曆

        Args:
            lunar_year: 農曆年
            lunar_month: 農曆月 (1-12)
            lunar_day: 農曆日 (1-30)

        Returns:
            對應的西曆日期，若無效則返回 None
        """
        try:
            from lunarcalendar import Converter, Lunar
            lunar = Lunar(lunar_year, lunar_month, lunar_day, isleap=False)
            solar = Converter.Lunar2Solar(lunar)
            return date(solar.year, solar.month, solar.day)
        except (ImportError, ValueError, Exception):
            # 無法轉換（可能是無效日期）
            return None

    def get_solar_dates_for_lunar(
        self,
        lunar_month: int,
        lunar_day: int,
        year_range: int = 20,
        center_year: Optional[int] = None
    ) -> list[dict]:
        """
        將農曆月日轉換為多年的西曆日期

        Args:
            lunar_month: 農曆月 (1-12)
            lunar_day: 農曆日 (1-30)
            year_range: 年份範圍（±N 年）
            center_year: 中心年份（預設為當前年份）

        Returns:
            西曆日期列表
        """
        from datetime import date as dt
        center = center_year or dt.today().year
        start_year = center - year_range
        end_year = center + year_range

        results = []
        for year in range(start_year, end_year + 1):
            solar_date = self.lunar_to_solar(year, lunar_month, lunar_day)
            if solar_date:
                results.append({
                    "lunar_year": year,
                    "solar_date": solar_date.isoformat(),
                    "display": f"{solar_date.year}/{solar_date.month}/{solar_date.day}"
                })

        return results

    def get_mansion_index(self, lunar_month: int, lunar_day: int) -> int:
        """
        根據農曆月日計算本命宿索引

        使用月宿傍通曆：每月初一有固定的起始宿，
        之後每天進一宿（27宿循環）

        Args:
            lunar_month: 農曆月份 (1-12)
            lunar_day: 農曆日期 (1-30)

        Returns:
            本命宿索引 (0-26)
        """
        # 處理閏月：使用對應的月份
        month = lunar_month if 1 <= lunar_month <= 12 else 1

        # 取得該月起始宿
        start = self.MONTH_START_MANSION.get(month, 0)

        # 每天進一宿
        return (start + lunar_day - 1) % 27

    # 全域參考點：農曆2026年正月初一 = 2026-02-17 = 室宿(11)
    # 用於日運連續宿位計算，確保每日恰好前進一宿
    _MANSION_REF_DATE = date(2026, 2, 17)
    _MANSION_REF_INDEX = 11  # 室宿

    def _get_corrected_mansion_index(self, solar_date: date) -> int:
        """日運用的修正後宿位（全域連續遞進，每日+1）

        以農曆2026年正月初一=室宿(11)為參考點，
        根據日數差計算任意日期的宿位。每日恰好前進一宿，
        不受月邊界 gap 或年邊界重置影響。

        本命宿仍使用 get_mansion_index（靜態表）。
        """
        days_diff = (solar_date - self._MANSION_REF_DATE).days
        return (self._MANSION_REF_INDEX + days_diff) % 27

    # 需要依語系切換的 mansion 欄位
    _MANSION_I18N_FIELDS = [
        'personality', 'love', 'career', 'health', 'seasonal',
        'keywords', 'life_stages',
    ]

    # lunar_date display 翻譯
    _LUNAR_DISPLAY = {
        'zh-TW': '農曆 {m} 月 {d} 日',
        'ja': '旧暦 {m} 月 {d} 日',
        'en': 'Lunar month {m}, day {d}',
    }

    def _localize_mansion(self, mansion: dict, lang: str) -> dict:
        """根據 lang 選擇 mansion 欄位的語系版本"""
        if lang == 'zh-TW' or lang not in self.SUPPORTED_LANGS:
            return dict(mansion)

        result = dict(mansion)
        suffix = '_ja' if lang == 'ja' else '_en'

        for field in self._MANSION_I18N_FIELDS:
            localized = mansion.get(f'{field}{suffix}')
            if localized:
                result[field] = localized

        # day_fortune 的 summary 和 auspicious/inauspicious
        if lang == 'en':
            df = mansion.get('day_fortune', {})
            df_en_summary = df.get('summary_en', '')
            df_en_auspicious = df.get('auspicious_en', [])
            df_en_inauspicious = df.get('inauspicious_en', [])
            if df_en_summary or df_en_auspicious:
                result['day_fortune'] = {
                    **df,
                    'summary': df_en_summary or df.get('summary', ''),
                    'auspicious': df_en_auspicious or df.get('auspicious', []),
                    'inauspicious': df_en_inauspicious or df.get('inauspicious', []),
                }
        elif lang == 'ja':
            df = mansion.get('day_fortune', {})
            df_ja_summary = df.get('summary_ja', '')
            if df_ja_summary:
                result['day_fortune'] = {**df, 'summary': df_ja_summary}

        return result

    def get_mansion(self, solar_date: date, lang: str = 'zh-TW') -> dict:
        """
        根據西曆生日取得本命宿資料

        Args:
            solar_date: 西曆生日
            lang: 語系

        Returns:
            包含本命宿完整資料的字典
        """
        lunar_year, lunar_month, lunar_day, is_leap = self.solar_to_lunar(solar_date)
        mansion_index = self.get_mansion_index(lunar_month, lunar_day)
        mansion = self.mansions_data[mansion_index]
        localized = self._localize_mansion(mansion, lang)

        display_fmt = self._LUNAR_DISPLAY.get(lang, self._LUNAR_DISPLAY['zh-TW'])
        return {
            **localized,
            "solar_date": solar_date.isoformat(),
            "lunar_date": {
                "year": lunar_year,
                "month": lunar_month,
                "day": lunar_day,
                "is_leap": is_leap,
                "display": display_fmt.format(m=lunar_month, d=lunar_day)
            }
        }

    def get_relation_type(self, index1: int, index2: int) -> dict:
        """
        計算兩個宿位之間的關係

        三九秘法：根據兩宿之間的距離判斷關係類型

        Args:
            index1: 第一個宿的索引 (0-26)
            index2: 第二個宿的索引 (0-26)

        Returns:
            關係資料（包含 distance_type 和 direction）
        """
        # 計算有向距離：從 index1 到 index2
        # forward_distance: index1 往前數幾格到 index2
        forward_distance = (index2 - index1) % 27

        # 檢查各種關係
        for rel_key, rel_data in self.relations_data.items():
            distances = rel_data["distances"]
            if forward_distance in distances:
                # 找到匹配的關係，計算距離類型和方向
                distance_type, direction = self._get_distance_info(rel_key, forward_distance)
                return {
                    "type": rel_key,
                    "distance_type": distance_type,
                    "distance_type_name": self._get_distance_type_name(distance_type),
                    "distance_type_reading": self._get_distance_type_reading(distance_type),
                    "direction": direction,
                    **rel_data
                }

        # 預設：未知關係（不應該發生）
        return {
            "type": "unknown",
            "name": "未知",
            "score": 50,
            "description": "無法判斷關係類型",
            "advice": "",
            "distance_type": None,
            "distance_type_name": "",
            "distance_type_reading": "",
            "direction": None
        }

    def _get_distance_info(self, rel_type: str, distance: int) -> tuple[Optional[str], Optional[str]]:
        """
        根據關係類型和距離，取得距離類型和方向

        Args:
            rel_type: 關係類型 (eishin, yusui, etc.)
            distance: 有向距離 (0-26)

        Returns:
            (distance_type, direction) - 如 ("near", "栄")
        """
        type_map = self.DISTANCE_TYPE_MAP.get(rel_type)
        if not type_map:
            return (None, None)

        for dist_type, config in type_map.items():
            if distance in config["distances"]:
                direction = config["direction_map"].get(distance)
                return (dist_type, direction)

        return (None, None)

    def _get_distance_type_name(self, distance_type: Optional[str]) -> str:
        """將距離類型轉換為中文名稱"""
        return {"near": "近距離", "mid": "中距離", "far": "遠距離"}.get(distance_type or "", "")

    def _get_distance_type_reading(self, distance_type: Optional[str]) -> str:
        """將距離類型轉換為假名讀音"""
        return {"near": "きんきょり", "mid": "ちゅうきょり", "far": "えんきょり"}.get(distance_type or "", "")

    def calculate_compatibility(
        self,
        date1: date,
        date2: date,
        lang: str = 'zh-TW',
        mode: str = 'seeker'
    ) -> dict:
        """
        計算兩人的相性

        Args:
            date1: 第一個人的西曆生日
            date2: 第二個人的西曆生日

        Returns:
            相性分析結果
        """
        mansion1 = self.get_mansion(date1)
        mansion2 = self.get_mansion(date2)

        relation = self.get_relation_type(mansion1["index"], mansion2["index"])

        # 計算距離
        distance = abs(mansion2["index"] - mansion1["index"])
        if distance > 13:
            distance = 27 - distance

        # 計算元素相性加成
        element_bonus = self._calculate_element_bonus(
            mansion1["element"],
            mansion2["element"]
        )

        # 取得元素資料
        elem1_data = self.elements_data.get(mansion1["element"], {})
        elem2_data = self.elements_data.get(mansion2["element"], {})

        # 綜合分數（等級映射 + 元素加成）
        rel_level = self.RELATION_LEVEL_MAP.get(relation["type"], "chukichi")
        base_score = self.LEVEL_DISPLAY_SCORE[rel_level] + element_bonus
        final_score = min(100, base_score)

        # 雙向分數（依方向能量流向調整）
        direction_p1 = relation.get("direction", "命")
        direction_p2 = self.DIRECTION_INVERSE.get(direction_p1, direction_p1)
        mod_p1 = self.DIRECTION_SCORE_MODIFIER.get(direction_p1, 0)
        mod_p2 = self.DIRECTION_SCORE_MODIFIER.get(direction_p2, 0)
        score_p1_to_p2 = min(100, max(10, base_score + mod_p1))
        score_p2_to_p1 = min(100, max(10, base_score + mod_p2))

        # 凌犯對配對的影響（凌犯是曆法期間，雙方同時受影響）
        today = date.today()
        ryouhan_today = self.check_ryouhan_period(today)
        ryouhan_active = ryouhan_today is not None
        # 凌犯逆轉：高分變低，低分變高
        ryouhan_score_p1 = (100 - score_p1_to_p2) if ryouhan_active else None
        ryouhan_score_p2 = (100 - score_p2_to_p1) if ryouhan_active else None

        # 載入 i18n 關係翻譯
        relations_i18n = self._load_relations_i18n(lang)
        rel_i18n = relations_i18n.get(relation["type"], {})

        # 取得距離化描述（如果有）
        dist_type = relation.get("distance_type")
        by_distance = relation.get("by_distance", {})
        by_distance_i18n = rel_i18n.get("by_distance", {})
        distance_detail = by_distance.get(dist_type, {}) if dist_type else {}
        distance_detail_i18n = by_distance_i18n.get(dist_type, {}) if dist_type else {}

        # 使用 i18n 翻譯覆蓋，fallback 到距離化描述，再 fallback 到通用描述
        rel_description = (
            distance_detail_i18n.get("description")
            or rel_i18n.get("description")
            or distance_detail.get("description")
            or relation["description"]
        )
        rel_advice = (
            distance_detail_i18n.get("advice")
            or rel_i18n.get("advice")
            or distance_detail.get("advice")
            or relation["advice"]
        )
        rel_tips = (
            distance_detail_i18n.get("tips")
            or rel_i18n.get("tips")
            or distance_detail.get("tips")
            or relation.get("tips", [])
        )
        rel_avoid = (
            distance_detail_i18n.get("avoid")
            or rel_i18n.get("avoid")
            or distance_detail.get("avoid")
            or relation.get("avoid", [])
        )

        return {
            "person1": {
                "date": date1.isoformat(),
                "mansion": mansion1["name_jp"],
                "reading": mansion1["reading"],
                "element": mansion1["element"],
                "element_reading": elem1_data.get("reading", ""),
                "element_traits": elem1_data.get("traits", ""),
                "keywords": self._get_mansion_keywords(mansion1, lang),
                "index": mansion1["index"]
            },
            "person2": {
                "date": date2.isoformat(),
                "mansion": mansion2["name_jp"],
                "reading": mansion2["reading"],
                "element": mansion2["element"],
                "element_reading": elem2_data.get("reading", ""),
                "element_traits": elem2_data.get("traits", ""),
                "keywords": self._get_mansion_keywords(mansion2, lang),
                "index": mansion2["index"]
            },
            "relation": {
                "type": relation["type"],
                "name": relation["name"],
                "name_jp": relation.get("name_jp", relation["name"]),
                "reading": relation.get("reading", ""),
                "description": rel_description,
                "detailed": rel_i18n.get("detailed") or relation.get("detailed", ""),
                "advice": rel_advice,
                "tips": rel_tips,
                "avoid": rel_avoid,
                "good_for": rel_i18n.get("good_for") or relation.get("good_for", []),
                "description_classic": rel_i18n.get("description_classic") or relation.get("description_classic", ""),
                "distance_type": relation.get("distance_type"),
                "distance_type_name": relation.get("distance_type_name", ""),
                "distance_type_reading": relation.get("distance_type_reading", ""),
                "direction": relation.get("direction"),
                "love": distance_detail_i18n.get("love") or distance_detail.get("love", ""),
                "career": self._build_career_with_sutra(
                    relation["type"],
                    distance_detail_i18n.get("career") or distance_detail.get("career", "")
                ),
                "roles": self._get_role_guidance(relation.get("direction", "命"))
            },
            "calculation": {
                "distance": distance,
                "formula": f"|{mansion1['index']} - {mansion2['index']}| = {abs(mansion2['index'] - mansion1['index'])} → 距離 {distance}",
                "element_relation": self._get_element_relation(mansion1["element"], mansion2["element"])
            },
            "score": final_score,
            "element_bonus": element_bonus,
            "directional_scores": {
                "person1_to_person2": {
                    "direction": direction_p1,
                    "score": score_p1_to_p2,
                    "modifier": mod_p1,
                    "ryouhan_active": ryouhan_active,
                    "ryouhan_adjusted_score": ryouhan_score_p1,
                },
                "person2_to_person1": {
                    "direction": direction_p2,
                    "score": score_p2_to_p1,
                    "modifier": mod_p2,
                    "ryouhan_active": ryouhan_active,
                    "ryouhan_adjusted_score": ryouhan_score_p2,
                },
            },
            "summary": self._generate_summary(mansion1, mansion2, relation, final_score),
            "classical_analysis": self.get_classical_analysis(mansion1["index"], mansion2["index"]),
            "direction_analysis": self.get_direction_analysis(relation.get("direction", "命"), mode, lang),
            "practical_guidance": self.get_practical_guidance(mansion1["index"], mansion2["index"]),
        }

    def get_classical_analysis(self, index1: int, index2: int) -> dict:
        """取得原典三九秘法分析

        根據 T21n1299《宿曜經》卷下的三九秘法，計算雙方在對方三九法中的位置，
        引用對應經文並提供白話解讀。

        Args:
            index1: person1 的宿曜 index (0-26)
            index2: person2 的宿曜 index (0-26)

        Returns:
            雙向原典分析結果
        """
        def _build_direction_view(source_idx: int, target_idx: int) -> dict:
            distance = (target_idx - source_idx) % 27
            position_name = self.SANKU_POSITION_NAMES[distance]
            group_number = (distance // 9) + 1
            group_info = self.SANKU_GROUP_NAMES[group_number]
            position_text = self.CLASSICAL_POSITION_TEXTS[position_name]

            source_mansion = self.mansions_data[source_idx]
            target_mansion = self.mansions_data[target_idx]
            src = source_mansion["name_jp"]
            tgt = target_mansion["name_jp"]

            # 將白話解讀中的「你/對方/此人」替換為實際宿名
            interp = position_text["interpretation"]
            interp = interp.replace("你們", f"{src}與{tgt}")
            interp = interp.replace("你的", f"{src}的")
            interp = interp.replace("此人", tgt)
            interp = interp.replace("對方", tgt)
            interp = interp.replace("你", src)

            return {
                "source_mansion": src,
                "target_mansion": tgt,
                "distance": distance,
                "group": {
                    "number": group_number,
                    "name": group_info["name"],
                    "reading": group_info["reading"],
                    "head": group_info["head"],
                },
                "position": {
                    "name": position_name,
                    "index_in_group": distance % 9,
                    "full_name": f"{group_info['name']}之{position_name}",
                },
                "sutra": {
                    "text": position_text["sutra"],
                    "ref": position_text["ref"],
                },
                "interpretation": interp,
            }

        return {
            "source": "T21n1299 宿曜經 卷下",
            "person1_to_person2": _build_direction_view(index1, index2),
            "person2_to_person1": _build_direction_view(index2, index1),
        }

    @staticmethod
    def _get_relation_type_for_direction(direction: str) -> str:
        """方向 → 關係類型 key（對應 relationship_verdicts）"""
        mapping = {
            "栄": "eishin", "親": "eishin",
            "友": "yusui", "衰": "yusui",
            "安": "ankai", "壊": "ankai",
            "危": "kisei", "成": "kisei",
            "命": "mei",
            "業": "gyotai", "胎": "gyotai",
        }
        return mapping.get(direction, "")

    def get_direction_analysis(self, direction: str, mode: str = "seeker", lang: str = "zh-TW") -> dict:
        """方向性深度分析：能量流動 + 職場意涵

        Args:
            direction: 方向標籤（栄/衰/安/危/成/壊/友/親/命/業/胎）
            mode: "seeker" (求職者看公司) 或 "hr" (公司看候選人)

        Returns:
            能量流動、雙方視角、職場建議、反方向資訊
        """
        direction_pairs = {
            "栄": "親", "親": "栄",
            "友": "衰", "衰": "友",
            "安": "壊", "壊": "安",
            "危": "成", "成": "危",
            "命": "命", "業": "胎", "胎": "業",
        }

        meaning = self.DIRECTION_CAREER_MEANINGS.get(direction, {})
        inverse = direction_pairs.get(direction, direction)
        inverse_meaning = self.DIRECTION_CAREER_MEANINGS.get(inverse, {})

        if mode == "personal":
            sutra_items = []
            inverse_sutra_items = []
        elif mode == "hr":
            sutra_items = self.get_hr_sutra_career_items(direction)
            inverse_sutra_items = self.get_hr_sutra_career_items(inverse)
        else:
            sutra_items = self.get_sutra_career_items(direction)
            inverse_sutra_items = self.get_sutra_career_items(inverse)

        # 從 guidance.json 取角色名和敘事（依 mode 選版本）
        guidance_json = self._load_guidance_json(lang)
        dir_data = guidance_json.get("directions", {}).get(direction, {})
        inv_data = guidance_json.get("directions", {}).get(inverse, {})
        if mode == "hr":
            nar_key = "narrative_hr"
        elif mode == "personal":
            nar_key = "narrative_personal"
        else:
            nar_key = "narrative"

        # 關係綜合判斷（relationship verdict）
        relation_type = self._get_relation_type_for_direction(direction)
        verdicts_data = guidance_json.get("relationship_verdicts", {})
        if mode == "hr":
            bl_key = "bottom_line_hr"
        elif mode == "personal":
            bl_key = "bottom_line_personal"
        else:
            bl_key = "bottom_line_seeker"
        verdict = None
        if relation_type in verdicts_data:
            side = f"{direction}方"
            verdict_entry = verdicts_data[relation_type].get(side)
            if verdict_entry:
                if mode == "personal":
                    v_text = verdict_entry.get("verdict_personal", verdict_entry.get("verdict", ""))
                    e_text = verdict_entry.get("explanation_personal", verdict_entry.get("explanation", ""))
                else:
                    v_text = verdict_entry.get("verdict", "")
                    e_text = verdict_entry.get("explanation", "")
                verdict = {
                    "severity": verdict_entry.get("severity", "neutral"),
                    "verdict": v_text,
                    "explanation": e_text,
                    "bottom_line": verdict_entry.get(bl_key, ""),
                }

        return {
            "verdict": verdict,
            "direction": direction,
            "role_name": dir_data.get("role_name", direction),
            "narrative": dir_data.get(nar_key, dir_data.get("narrative", "")),
            "energy_flow": meaning.get("energy_flow", ""),
            "person1_perspective": meaning.get("as_person1", ""),
            "person2_perspective": meaning.get("as_person2", ""),
            "career_tip": self._get_practical_career(direction),
            "sutra_career_items": sutra_items,
            "guidance": self.get_direction_guidance(direction, mode, lang),
            "inverse_direction": inverse,
            "inverse_role_name": inv_data.get("role_name", inverse),
            "inverse_narrative": inv_data.get(nar_key, inv_data.get("narrative", "")),
            "inverse_meaning": inverse_meaning.get("energy_flow", ""),
            "inverse_sutra_career_items": inverse_sutra_items,
            "inverse_guidance": self.get_direction_guidance(inverse, mode, lang),
        }

    def get_practical_guidance(self, index1: int, index2: int) -> dict:
        """根據三九秘法位置產出現代行動建議

        Args:
            index1: person1 的宿曜 index (0-26)
            index2: person2 的宿曜 index (0-26)

        Returns:
            雙向實用行動建議（宜做/忌做/職場建議）
        """
        def _build_guidance(source_idx: int, target_idx: int) -> dict:
            distance = (target_idx - source_idx) % 27
            position_name = self.SANKU_POSITION_NAMES[distance]
            actions = self.PRACTICAL_ACTION_MAP.get(position_name, {})
            return {
                "position": position_name,
                "do": actions.get("do", []),
                "avoid": actions.get("avoid", []),
                "career_advice": self._get_practical_career(position_name),
            }

        return {
            "person1_to_person2": _build_guidance(index1, index2),
            "person2_to_person1": _build_guidance(index2, index1),
        }

    def _get_element_relation(self, elem1: str, elem2: str) -> str:
        """取得元素關係說明"""
        GENERATING = {
            ("木", "火"): "木生火",
            ("火", "土"): "火生土",
            ("土", "金"): "土生金",
            ("金", "水"): "金生水",
            ("水", "木"): "水生木",
            ("日", "火"): "日生火",
            ("月", "水"): "月生水"
        }

        if elem1 == elem2:
            return f"同元素（{elem1}）+10 分"

        pair = (elem1, elem2)
        reverse_pair = (elem2, elem1)

        if pair in GENERATING:
            return f"{GENERATING[pair]} +5 分"
        if reverse_pair in GENERATING:
            return f"{GENERATING[reverse_pair]} +5 分"

        return "無特殊加成"

    def _calculate_element_bonus(self, elem1: str, elem2: str) -> int:
        """計算元素相性加成"""
        # 五行相生：木生火、火生土、土生金、金生水、水生木
        # 日月特殊：日生火、月生水
        GENERATING = [
            ("木", "火"),
            ("火", "土"),
            ("土", "金"),
            ("金", "水"),
            ("水", "木"),
            ("日", "火"),
            ("月", "水")
        ]

        if elem1 == elem2:
            return 10  # 同元素加分

        pair = (elem1, elem2)
        reverse_pair = (elem2, elem1)

        if pair in GENERATING or reverse_pair in GENERATING:
            return 5  # 相生加分

        return 0

    def _generate_summary(
        self,
        mansion1: dict,
        mansion2: dict,
        relation: dict,
        calculated_score: int
    ) -> str:
        """生成相性總結"""
        rel_name = relation["name"]
        name1 = mansion1["name_jp"]
        name2 = mansion2["name_jp"]

        if calculated_score >= 90:
            level = "非常合拍"
        elif calculated_score >= 75:
            level = "相當不錯"
        elif calculated_score >= 60:
            level = "需要磨合"
        else:
            level = "要多小心"

        return (
            f"{name1}與{name2}的關係是「{rel_name}」，整體評價：{level}。\n"
            f"{relation['description']}\n"
            f"建議：{relation['advice']}"
        )

    def get_all_mansions(self, lang: str = 'zh-TW') -> list[dict]:
        """取得所有 27 宿資料"""
        return [self._localize_mansion(m, lang) for m in self.mansions_data]

    def get_mansion_lunar_dates(self, mansion_index: int) -> list[dict]:
        """
        取得某個宿位對應的農曆生日範圍

        Args:
            mansion_index: 宿位索引 (0-26)

        Returns:
            對應的農曆月日列表
        """
        results = []

        # 每個月檢查哪些日期會對應到這個宿位
        for month, start_mansion in self.MONTH_START_MANSION.items():
            # 計算這個月的哪一天對應到目標宿位
            # mansion_index = (start_mansion + day - 1) % 27
            # day = (mansion_index - start_mansion + 1) % 27
            # 如果結果 <= 0，加 27

            day = (mansion_index - start_mansion + 1) % 27
            if day <= 0:
                day += 27

            # 農曆每月最多 30 天，只取有效日期
            if 1 <= day <= 30:
                month_names = {
                    1: "正月", 2: "二月", 3: "三月", 4: "四月",
                    5: "五月", 6: "六月", 7: "七月", 8: "八月",
                    9: "九月", 10: "十月", 11: "十一月", 12: "十二月"
                }
                results.append({
                    "lunar_month": month,
                    "lunar_month_name": month_names[month],
                    "lunar_day": day,
                    "display": f"{month_names[month]}{day}日"
                })

        return results

    def find_compatible_mansions(self, solar_date: date, lang: str = 'zh-TW') -> dict:
        """
        根據生日找出最佳配對與需要避免的本命宿

        Args:
            solar_date: 西曆生日

        Returns:
            包含栄親、業胎、安壊三類配對宿位的資料
        """
        mansion = self.get_mansion(solar_date)
        user_index = mansion["index"]

        # 各關係類型的距離定義（完整六種關係）
        COMPATIBILITY_TYPES = {
            "mei": {
                "relation": "命",
                "reading": "めい",
                "distances": [0],
                "score": 85,
                "description": "如同鏡子般的存在，彼此理解但優缺點皆被放大",
                "detailed": "命宿之人擁有相同的宿星，等於遇見另一個自己。你們不需要多餘的解釋就能理解對方在想什麼，默契好到讓旁人羨慕。但這面鏡子也會毫不留情地映照出你不想面對的缺點——你身上那些讓自己煩躁的特質，對方也會有。相處的關鍵在於把對方當成自我成長的參照，而不是互相放大弱點。能做到這點的話，這是一段可以走很遠的關係。"
            },
            "gyotai": {
                "relation": "業胎",
                "reading": "ぎょうたい",
                "distances": [9, 18],
                "score": 90,
                "description": "前世因緣深厚，常有似曾相識之感",
                "detailed": "業胎是宿曜道中最神秘的關係。初次見面就覺得對方好像認識了很久，聊起天來完全沒有陌生感。宿曜道認為這是前世累積的緣分在今生延續。這段關係的特點是自然、不費力，你們不需要刻意經營就能維持默契。但也正因如此，容易把對方的存在視為理所當然。記得偶爾表達感謝，讓這份難得的緣分持續發酵。"
            },
            "eishin": {
                "relation": "栄親",
                "reading": "えいしん",
                "distances": [1, 8, 10, 17, 19, 26],
                "score": 95,
                "description": "最適合結婚的對象，互相提攜成長的良緣",
                "detailed": "栄親在宿曜道中被視為最理想的結合。你們的能量場互相加持，一方有光芒時另一方也會跟著閃耀。不是那種激烈的來電，而是越相處越覺得「跟這個人在一起什麼都會變好」的踏實感。在職場上你們是天然的好搭檔，在感情中是能共同成長的伴侶。維持這段關係的秘訣是讓彼此都有發光的舞台，不要只有一方在付出。"
            },
            "yusui": {
                "relation": "友衰",
                "reading": "ゆうすい",
                "distances": [2, 7, 11, 16, 20, 25],
                "score": 70,
                "description": "相處舒適自在，但需注意不要一起停滯不前",
                "detailed": "友衰的友方會覺得跟對方在一起很舒服，衰方則可能不自覺地消耗精力。這種關係初期很迷人——你們聊得來、價值觀接近、在一起總是很開心。但長期下來，如果沒有刻意地互相激勵，容易變成一起追劇一起抱怨但都不行動的狀態。經營這段關係的方法是設定共同目標，用正向的壓力推著彼此前進。"
            },
            "ankai": {
                "relation": "安壊",
                "reading": "あんかい",
                "distances": [3, 6, 12, 15, 21, 24],
                "score": 50,
                "description": "強烈吸引力但權力不對等，需謹慎經營",
                "detailed": "安壊是宿曜道中最有戲劇性的關係。安方會被壊方強烈吸引，壊方則不自覺地對安方施加壓力。這種不對等的能量讓關係充滿張力和刺激感。如果雙方都能意識到這種動態並刻意平衡，反而能碰撞出驚人的火花。這段關係需要比其他關係更用心地維護——建立明確的界線、養成坦誠溝通的習慣、在張力出現時主動踩煞車。用對方法，安壊關係能成為推動彼此成長的強大力量。"
            },
            "kisei": {
                "relation": "危成",
                "reading": "きせい",
                "distances": [4, 5, 13, 14, 22, 23],
                "score": 75,
                "description": "互補的關係，需要磨合但能促進彼此成長",
                "detailed": "危成是一段「不磨合就無法前進，但磨合之後特別堅固」的關係。成方帶來穩定和規劃能力，危方帶來突破和冒險精神。初期你們可能對對方的做事方式感到困惑甚至不耐煩，但這種差異正是讓你們各自補足盲點的機會。經歷過幾次衝突和理解之後，你們會變成一個攻守兼備的組合。耐心是這段關係的必要投資。"
            }
        }

        result = {
            "your_mansion": {
                "name_jp": mansion["name_jp"],
                "name_zh": mansion["name_zh"],
                "reading": mansion["reading"],
                "index": user_index,
                "element": mansion["element"],
                "lunar_date": mansion["lunar_date"]
            }
        }

        # 計算各類型的配對宿位
        for key, config in COMPATIBILITY_TYPES.items():
            indices = set()
            for d in config["distances"]:
                indices.add((user_index + d) % 27)
                indices.add((user_index - d + 27) % 27)

            # 取得這些宿位的詳細資料
            mansions = []
            for idx in sorted(indices):
                m = self.mansions_data[idx]
                elem_data = self.elements_data.get(m["element"], {})
                lunar_dates = self.get_mansion_lunar_dates(idx)

                # 為每個農曆日期加上西曆對照
                for ld in lunar_dates:
                    ld["solar_dates"] = self.get_solar_dates_for_lunar(
                        ld["lunar_month"],
                        ld["lunar_day"],
                        year_range=25,
                        center_year=solar_date.year
                    )

                mansions.append({
                    "name_jp": m["name_jp"],
                    "name_zh": m["name_zh"],
                    "reading": m["reading"],
                    "index": idx,
                    "element": m["element"],
                    "element_reading": elem_data.get("reading", ""),
                    "keywords": self._get_mansion_keywords(m, lang),
                    "personality": m["personality"],
                    "lunar_dates": lunar_dates
                })

            result[key] = {
                "relation": config["relation"],
                "reading": config["reading"],
                "score": config["score"],
                "description": config["description"],
                "detailed": config.get("detailed", ""),
                "mansions": mansions
            }

        return result

    # ==================== 運勢計算 ====================

    def _load_fortune_data(self):
        """載入運勢資料"""
        if not hasattr(self, '_fortune_data') or self._fortune_data is None:
            data_path = Path(__file__).parent.parent / "data" / "sukuyodo_fortune.json"
            with open(data_path, "r", encoding="utf-8") as f:
                self._fortune_data = json.load(f)
        return self._fortune_data

    def _load_fortune_i18n(self, lang: str) -> dict:
        """載入 fortune_data 的 i18n 翻譯 (有快取)"""
        if lang in self._fortune_i18n_cache:
            return self._fortune_i18n_cache[lang]
        if lang not in self.SUPPORTED_LANGS:
            lang = self.DEFAULT_LANG
        i18n_path = Path(__file__).parent.parent / "data" / "i18n" / lang / "fortune_data.json"
        if not i18n_path.exists():
            i18n_path = Path(__file__).parent.parent / "data" / "i18n" / "zh-TW" / "fortune_data.json"
        if i18n_path.exists():
            with open(i18n_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = {}
        self._fortune_i18n_cache[lang] = data
        return data

    def _get_fortune_element_desc(self, relation_type: str, lang: str = 'zh-TW') -> str:
        """取得元素關係描述（支援多語系）"""
        fortune_i18n = self._load_fortune_i18n(lang)
        i18n_desc = fortune_i18n.get("element_relations", {}).get(relation_type, {}).get("description")
        if i18n_desc:
            return i18n_desc
        # fallback 到原始 fortune_data
        fortune_data = self._load_fortune_data()
        return fortune_data["element_relations"].get(
            relation_type,
            fortune_data["element_relations"]["neutral"]
        )["description"]

    def _get_mansion_keywords(self, mansion: dict, lang: str = 'zh-TW') -> list:
        """根據語系取得宿位關鍵字"""
        if lang == 'ja' and 'keywords_ja' in mansion:
            return mansion['keywords_ja']
        return mansion['keywords']

    def _load_sanki_i18n(self, lang: str) -> dict:
        """載入三期 i18n 翻譯 (有快取)"""
        cache_key = f"sanki_{lang}"
        if cache_key in self._fortune_i18n_cache:
            return self._fortune_i18n_cache[cache_key]
        if lang not in self.SUPPORTED_LANGS:
            lang = self.DEFAULT_LANG
        i18n_path = Path(__file__).parent.parent / "data" / "i18n" / lang / "sanki.json"
        if not i18n_path.exists():
            i18n_path = Path(__file__).parent.parent / "data" / "i18n" / "zh-TW" / "sanki.json"
        if i18n_path.exists():
            with open(i18n_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = {}
        self._fortune_i18n_cache[cache_key] = data
        return data

    _day_fortune_items_cache: dict[str, dict] = {}

    def _load_day_fortune_items(self, lang: str) -> dict:
        """載入 day_fortune 吉凶項目翻譯 mapping"""
        if lang in self._day_fortune_items_cache:
            return self._day_fortune_items_cache[lang]
        if lang != 'ja':
            return {}
        items_path = Path(__file__).parent.parent / "data" / "i18n" / "ja" / "day_fortune_items.json"
        if not items_path.exists():
            return {}
        with open(items_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self._day_fortune_items_cache[lang] = data
        return data

    def _get_day_fortune_i18n(self, day_fortune_data: dict, lang: str = 'zh-TW') -> dict:
        """根據語系替換 day_fortune 的 summary + auspicious/inauspicious"""
        if not day_fortune_data:
            return day_fortune_data
        result = dict(day_fortune_data)
        if lang == 'ja':
            if 'summary_ja' in result:
                result['summary'] = result['summary_ja']
            items_map = self._load_day_fortune_items(lang)
            if items_map:
                result['auspicious'] = [items_map.get(a, a) for a in result.get('auspicious', [])]
                result['inauspicious'] = [items_map.get(a, a) for a in result.get('inauspicious', [])]
        elif lang == 'en':
            if 'summary_en' in result:
                result['summary'] = result['summary_en']
            if 'auspicious_en' in result:
                result['auspicious'] = result['auspicious_en']
            if 'inauspicious_en' in result:
                result['inauspicious'] = result['inauspicious_en']
        return result

    def _get_element_relation_type_name(self, relation_type: str, lang: str = 'zh-TW') -> str:
        """取得元素關係類型的翻譯顯示名稱"""
        fortune_i18n = self._load_fortune_i18n(lang)
        type_names = fortune_i18n.get("element_relation_type_names", {})
        if relation_type in type_names:
            return type_names[relation_type]
        # fallback 預設
        defaults = {
            "same": "同元素",
            "generating": "相生",
            "weakening": "相洩",
            "conflicting": "相剋",
            "neutral": "平穩"
        }
        return defaults.get(relation_type, relation_type)

    def _get_fortune_advice(self, advice_key: str, lang: str = 'zh-TW') -> list:
        """取得日運建議列表（支援多語系）"""
        fortune_i18n = self._load_fortune_i18n(lang)
        i18n_advice = fortune_i18n.get("daily_advice", {}).get(advice_key)
        if i18n_advice:
            return i18n_advice
        # fallback 到原始 fortune_data
        fortune_data = self._load_fortune_data()
        return fortune_data["daily_advice"].get(advice_key, fortune_data["daily_advice"]["neutral"])

    def _get_fortune_lucky_items(self, lang: str = 'zh-TW') -> dict:
        """取得幸運物品資料（支援多語系，覆蓋 color/direction 顯示名稱）"""
        fortune_data = self._load_fortune_data()
        lucky = fortune_data["lucky_items"]
        fortune_i18n = self._load_fortune_i18n(lang)
        i18n_lucky = fortune_i18n.get("lucky_items", {})
        if not i18n_lucky:
            return lucky
        # 覆蓋 direction/color 的顯示名稱
        result = {
            "directions": {},
            "colors": {},
            "numbers": lucky.get("numbers", {})
        }
        for elem, dir_data in lucky["directions"].items():
            result["directions"][elem] = dict(dir_data)
            i18n_dir = i18n_lucky.get("directions", {}).get(elem)
            if i18n_dir:
                result["directions"][elem]["direction"] = i18n_dir
        for elem, color_data in lucky["colors"].items():
            result["colors"][elem] = dict(color_data)
            i18n_color = i18n_lucky.get("colors", {}).get(elem)
            if i18n_color:
                result["colors"][elem]["color"] = i18n_color
        return result

    def _get_fortune_monthly_theme(self, month: int, lang: str = 'zh-TW') -> dict:
        """取得月份主題（支援多語系）"""
        fortune_i18n = self._load_fortune_i18n(lang)
        i18n_theme = fortune_i18n.get("monthly_themes", {}).get(str(month))
        if i18n_theme:
            # 與原始資料合併（保留 element_boost 等不翻譯欄位）
            fortune_data = self._load_fortune_data()
            base_theme = fortune_data["monthly_themes"].get(str(month), {})
            return {**base_theme, **i18n_theme}
        fortune_data = self._load_fortune_data()
        return fortune_data["monthly_themes"].get(str(month), {})

    def _get_fortune_category_name(self, category: str, lang: str = 'zh-TW') -> str:
        """取得運勢分類名稱（支援多語系）"""
        fortune_i18n = self._load_fortune_i18n(lang)
        i18n_name = fortune_i18n.get("fortune_categories", {}).get(category, {}).get("name")
        if i18n_name:
            return i18n_name
        fortune_data = self._load_fortune_data()
        return fortune_data["fortune_categories"].get(category, {}).get("name", category)

    def _calc_fortune_element_relation(self, elem1: str, elem2: str) -> tuple[str, int]:
        """
        計算運勢用的元素關係

        Returns:
            (關係類型, 加成分數)
        """
        fortune_data = self._load_fortune_data()

        if elem1 == elem2:
            return ("same", fortune_data["element_relations"]["same"]["bonus"])

        # 相生（有方向性）：環境元素(elem2)生用戶元素(elem1) → 有利
        for pair in fortune_data["generating_pairs"]:
            if elem2 == pair[0] and elem1 == pair[1]:
                return ("generating", fortune_data["element_relations"]["generating"]["bonus"])

        # 相洩（有方向性）：用戶元素(elem1)生環境元素(elem2) → 能量被消耗
        for pair in fortune_data["generating_pairs"]:
            if elem1 == pair[0] and elem2 == pair[1]:
                return ("weakening", fortune_data["element_relations"]["weakening"]["bonus"])

        # 相剋（維持雙向）
        for pair in fortune_data["conflicting_pairs"]:
            if (elem1 == pair[0] and elem2 == pair[1]) or \
               (elem1 == pair[1] and elem2 == pair[0]):
                return ("conflicting", fortune_data["element_relations"]["conflicting"]["bonus"])

        # 日/月特殊處理：使用 special_elements 資料
        # 日生火、月生水，需區分方向性
        special = fortune_data.get("special_elements", {})
        for special_elem in ["日", "月"]:
            if elem1 == special_elem or elem2 == special_elem:
                other = elem2 if elem1 == special_elem else elem1
                spec = special.get(special_elem, {})
                if other in spec.get("generates", []):
                    if elem1 == special_elem:
                        # 用戶元素是日/月，生出環境元素 → 能量被消耗
                        return ("weakening", fortune_data["element_relations"]["weakening"]["bonus"])
                    else:
                        # 環境元素是日/月，生出用戶元素 → 用戶被生
                        return ("generating", fortune_data["element_relations"]["generating"]["bonus"])
                return ("neutral", fortune_data["element_relations"]["neutral"]["bonus"])

        return ("neutral", fortune_data["element_relations"]["neutral"]["bonus"])

    # === 等級優先制常數（原典依據） ===

    # 日運勢五等級（三九秘法）：index 0 = 最佳, index 4 = 最差
    FORTUNE_LEVELS = ["daikichi", "kichi", "chukichi", "shokyo", "kyo"]

    # 關係類型 → 等級映射（用於相性和日運等級判定）
    # 注意：mei(命)=kichi 指「同宿的深層連結」在相性中為吉，
    #       與三九日型「命の日不宜舉動百事」(T21 p.391b)的禁忌含義不同。
    #       日運禁忌在 _evaluate_day_quality 中由 SANKI_DAY_TYPES 另行處理。
    RELATION_LEVEL_MAP = {
        "eishin": "daikichi",  # 栄親 → 大吉
        "gyotai": "kichi",     # 業胎 → 吉
        "mei": "kichi",        # 命 → 吉（相性用途，非三九日運禁忌）
        "yusui": "chukichi",   # 友衰 → 中吉
        "kisei": "shokyo",     # 危成 → 小凶
        "ankai": "kyo",        # 安壊 → 凶
    }

    # 凌犯翻轉（對稱鏡射）
    RYOUHAN_LEVEL_FLIP = {
        "daikichi": "kyo",
        "kichi": "shokyo",
        "chukichi": "chukichi",  # 中吉不變
        "shokyo": "kichi",
        "kyo": "daikichi",
    }

    # 等級 → 顯示分數（UI 進度條用）
    LEVEL_DISPLAY_SCORE = {
        "daikichi": 90,
        "kichi": 75,
        "chukichi": 60,
        "shokyo": 45,
        "kyo": 35,
    }

    # 方向分數修正 — 依原典能量流向調整
    # 正值=該方向受益，負值=該方向付出
    DIRECTION_SCORE_MODIFIER = {
        "栄": 5,    # 被提升方，獲得成長
        "親": -3,   # 栽培方，付出資源
        "友": 5,    # 友好方，主動經營
        "衰": -8,   # 被消耗方，能量流失
        "安": -10,  # 安定方，持續付出穩定
        "壊": 15,   # 受益方，接受資源
        "危": -5,   # 承受壓力方
        "成": 10,   # 獲得成就方
        "命": 0,    # 對稱
        "業": -3,   # 過去因，背負
        "胎": 3,    # 未來果，成長
    }

    # 方向配對（反方向查找）
    DIRECTION_INVERSE = {
        "栄": "親", "親": "栄",
        "友": "衰", "衰": "友",
        "安": "壊", "壊": "安",
        "危": "成", "成": "危",
        "命": "命", "業": "胎", "胎": "業",
    }

    # 等級 → 中日文名稱
    LEVEL_NAMES = {
        "daikichi": {"zh": "大吉", "ja": "大吉", "en": "Great Fortune", "reading": "だいきち"},
        "kichi": {"zh": "吉", "ja": "吉", "en": "Good Fortune", "reading": "きち"},
        "chukichi": {"zh": "中吉", "ja": "中吉", "en": "Fair Fortune", "reading": "ちゅうきち"},
        "shokyo": {"zh": "小凶", "ja": "小凶", "en": "Minor Caution", "reading": "しょうきょう"},
        "kyo": {"zh": "凶", "ja": "凶", "en": "Caution", "reading": "きょう"},
    }

    # 等級 → effective_interpretation
    LEVEL_INTERPRETATION = {
        "daikichi": "excellent",
        "kichi": "good",
        "chukichi": "neutral",
        "shokyo": "challenging",
        "kyo": "caution",
    }

    # 等級 → advice key
    LEVEL_ADVICE_KEY = {
        "daikichi": "excellent",
        "kichi": "good",
        "chukichi": "neutral",
        "shokyo": "caution",
        "kyo": "challenging",
    }

    # 等級 → 描述選擇 key
    LEVEL_DESC_KEY = {
        "daikichi": "excellent",
        "kichi": "good",
        "chukichi": "fair",
        "shokyo": "caution",
        "kyo": "warning",
    }

    # 凌犯中等級 → 描述選擇 key
    RYOUHAN_DESC_KEY = {
        "daikichi": "high_reversal",
        "kichi": "high_reversal",
        "chukichi": "mid_reversal",
        "shokyo": "low_reversal",
        "kyo": "low_reversal",
    }

    # 九曜四等級 → 顯示分數（獨立體系）
    KUYOU_LEVEL_MAP = {
        "大吉": 85,
        "半吉": 65,
        "末吉": 50,
        "大凶": 35,
    }

    # 每日運勢專用描述（以 T21n1299 品二各日吉凶為基礎）
    # 每條描述 = 原典依據 → 白話行動建議
    DAILY_FORTUNE_DESCRIPTIONS = {
        # 栄「宜入官拜職、對見大人、上書表進獻君王、興營買賣」(p.397c)
        # 親「宜結交、定婚姻、歡宴聚會並吉」(p.397c)
        "eishin": [
            "原典記載栄日「宜入官拜職、對見大人」，親日「宜結交、歡宴聚會並吉」。今天適合主動出擊：面試、提案、見主管、拓展人脈，行動會有回報。",
            "栄日「宜興營買賣」（T21 p.397c），今天適合推進跟業務、合作、簽約有關的事。如果有懸而未決的案子，趁今天推一把。",
            "親日「宜結交、歡宴聚會並吉」（T21 p.397c），今天社交場合容易遇到能長期合作的人。需要別人幫忙的事，開口就對了。",
            "栄日「上書表進獻君王」（T21 p.397c），今天的提案、報告、建議書特別容易被接受。把準備好的東西送出去，時機對。",
            "栄親日全面吉利（T21 p.397c）。不管是爭取升遷、拓展業務、還是社交聚會，今天的行動力和判斷力都在高點，放手去做。",
        ],
        # 業「所作善惡亦不成就、甚衰」(p.397c)
        # 胎「不宜舉動百事」(p.397c) + 「宜修功德」(品三 p.391b)
        "gyotai": [
            "原典記載業日「所作善惡亦不成就，甚衰」，胎日「不宜舉動百事」。今天不管做什麼都不容易有結果，最好的策略是不主動出擊，安靜做好手邊的事。",
            "業日「甚衰」（T21 p.397c），今天的運勢在低點。不適合爭取、談判、開始新事物。把精力放在不需要外界回應的事情上，例如整理資料、學習充電。",
            "胎日「不宜舉動百事」（T21 p.397c），今天不是起頭的日子。計畫中的新專案、重要對話、大額交易都建議延後，等待更好的時機。",
            "業日「所作善惡亦不成就」（T21 p.397c），好事壞事都難有結果。與其勉強推進，不如利用這天默默累積實力，為之後的行動做準備。",
            "品三記載「宜修功德」，雖然不適合對外行動，但適合向內充實：讀書、進修、反省、整理思緒。蹲低是為了跳更高。",
        ],
        # 命「不宜舉動百事」(p.397c) + 「宜修功德」(品三 p.391b)
        "mei": [
            "原典記載命日「不宜舉動百事」。今天不適合主動發起任何重要事務，靜守本分、做好份內的事就好。",
            "命日本命宿回歸，原典說「不宜舉動」。不爭不搶的一天，把精力放在自我檢視和盤點上，比對外衝刺更有收穫。",
            "品三記載命日「宜修功德」，雖然不宜對外行動，但適合自我充實。讀書、反省、規劃未來方向，安靜地為下一步做準備。",
            "命日（T21 p.397c「不宜舉動百事」）不宜做重大決定。如果今天有人催你表態或簽字，能緩就緩。不是逃避，是時機不對。",
            "本命宿日（T21 p.397c）適合面對自己。最近的工作方向對不對、生活節奏好不好，趁今天靜下來想清楚，比急著行動有用。",
        ],
        # 友「宜結交朋友大吉、歡宴聚會並吉」(p.397c, p.391b)
        # 衰「唯宜解除諸惡、療病」「不宜出入遷移、買賣」(p.398a, p.391b)
        "yusui": [
            "原典記載友日「宜結交朋友大吉」，衰日「唯宜解除諸惡、療病」「不宜出入遷移、買賣」。社交聚會吉，但不適合搬遷、跳槽、大筆交易。",
            "友日「宜結交朋友大吉」（T21 p.391b），今天的人際互動會比平時順暢。聚餐、聊天、拓展人脈都好，但聊歸聊，大生意先不要今天談。",
            "衰日「唯宜解除諸惡、療病」（T21 p.398a），適合處理累積的問題和待辦事項。手頭有什麼拖著沒解決的，趁今天清掉。",
            "衰日「不宜出入遷移、買賣」（T21 p.398a），不是出差、搬家、簽大合約的好日子。能推到後面就推，急不來的事不要硬排今天。",
            "友衰日（T21 p.397c-398a）的節奏：對人好、對事慢。多跟人聊聊、吃頓飯，但工作上維持現狀就好，不需要急著做什麼大動作。",
        ],
        # 危「宜結交、歡宴聚會並吉」「不宜遠行出入移徙、買賣」(p.397c, p.398a)
        # 成「宜修道學問、合和長年藥法、作諸成就法並吉」(p.398a)
        "kisei": [
            "原典記載危日「宜結交、歡宴聚會並吉」「不宜遠行買賣」，成日「宜修道學問、作諸成就法並吉」。社交和學習吉，出差和大額交易不宜。",
            "成日「宜修道學問」（T21 p.398a），今天特別適合學習、進修、考試準備。需要專注力的工作拿到今天做，效率會不錯。",
            "危日「宜結交、歡宴聚會並吉」（T21 p.397c-398a），今天的社交場合容易有收穫。聚餐、團建、業界交流都好。",
            "危日「不宜遠行出入移徙、買賣」（T21 p.397c-398a），今天不適合出差、搬遷、或簽大筆合約。需要出遠門的事排到別天。",
            "成日「作諸成就法並吉」（T21 p.398a），正在進行中的專案今天適合收尾。學習中的東西今天特別容易融會貫通。",
        ],
        # 安「移徙吉、遠行人入宅、造作園宅、作壇場並吉」(p.397c)
        # 壊「宜作鎮壓、降伏怨讎、餘並不堪」(p.398a)
        "ankai": [
            "原典記載安日「移徙吉、造作園宅」，壊日「宜作鎮壓、降伏怨讎，餘並不堪」。安頓環境吉，處理棘手問題可行，其餘事不宜勉強。",
            "安日「移徙吉」（T21 p.397c），如果今天有搬遷、轉調、整理工作環境的需求，放手去做。安頓的事情今天做起來特別順。",
            "壊日「宜作鎮壓、降伏怨讎」（T21 p.398a），有棘手的問題或難纏的對手，今天處理反而能見效。但記住「餘並不堪」，其他事不要硬推。",
            "安日「造作園宅、作壇場並吉」（T21 p.397c），適合建立新制度、設定工作流程、整理辦公空間。把環境和基礎打好。",
            "壊日「餘並不堪」（T21 p.398a），除了處理棘手問題之外，其他重大事務建議延後。不是你做不好，是今天的時機不支持。",
        ]
    }

    # 每日運勢關係名稱（以 T21n1299 品二各日吉凶為準）
    # eishin: 栄「宜入官拜職...」親「宜結交...」→ 全吉
    # yusui: 友「宜結交大吉」衰「唯宜解除、不宜遷移買賣」→ 半吉半忌
    # kisei: 危「宜結交、不宜遠行買賣」成「宜修道學問」→ 半吉半忌
    # ankai: 安「移徙吉」壊「餘並不堪」→ 限定吉
    # mei: 「不宜舉動百事」→ 靜守
    # gyotai: 業「甚衰」胎「不宜舉動百事」→ 要注意
    DAILY_FORTUNE_RELATION_NAMES = {
        "eishin": {"zh": "大吉", "ja": "大吉", "en": "Excellent"},
        "yusui": {"zh": "半吉", "ja": "半吉", "en": "Mixed"},
        "kisei": {"zh": "半吉", "ja": "半吉", "en": "Mixed"},
        "ankai": {"zh": "要注意", "ja": "要注意", "en": "Caution"},
        "mei": {"zh": "靜守", "ja": "靜守", "en": "Rest"},
        "gyotai": {"zh": "要注意", "ja": "要注意", "en": "Caution"}
    }

    # 每日運勢各項描述（以 T21n1299 品二各日宜忌為基礎）
    # 5 個區間：excellent(85+), good(70-84), fair(55-69), caution(40-54), warning(<40)
    # career: 源自品二「入官拜職/興營買賣/修道學問」等職場相關經文
    # love: 源自品二「結交/定婚姻/歡宴聚會」等人際相關經文
    # health: 源自品二「療病/解除諸惡」+ 品三凌犯化解「修功德」等養生相關經文
    # wealth: 源自品二「興營買賣/不宜買賣」等財務相關經文
    DAILY_CATEGORY_DESCRIPTIONS = {
        "career": {
            "excellent": [
                "栄日「宜入官拜職、對見大人」（T21 p.397c）的格局。今天適合爭取升遷、面見主管、提交重要提案，行動會被看見、被接受。",
                "栄日「上書表進獻君王、興營買賣」（T21 p.397c），今天的報告、企劃、業務拓展都容易有好結果。該推的案子趁今天推。",
                "栄親日全面吉利（T21 p.397c）。面試、談判、簽約都好，把握今天主動出擊。",
            ],
            "good": [
                "成日「宜修道學問、作諸成就法」（T21 p.398a），今天適合推進手邊的專案、學習新技能，努力容易有成果。",
                "友日「宜結交朋友大吉」（T21 p.391b）的氣場帶動工作上的合作。跟同事、客戶的互動今天比較順暢。",
                "安日「造作園宅並吉」（T21 p.397c），今天適合建立制度、整理工作流程，把基礎打好。",
            ],
            "fair": [
                "安危日吉凶參半（T21 p.397c-398a），按部就班處理日常工作即可。不需要刻意求表現，做好份內的事就好。",
                "安日「造作園宅並吉」（T21 p.397c），今天適合處理例行事務：整理檔案、回覆郵件、更新報告。不急著做大決定。",
                "危日有宜有忌（T21 p.397c-398a），工作上沒有特別的助力也沒有阻礙，維持平穩節奏就好。",
            ],
            "caution": [
                "衰日「不宜出入遷移、買賣」（T21 p.398a），今天職場上不適合大動作。把精力放在手頭的問題上，不要急著拓展。",
                "壊日「餘並不堪」（T21 p.398a），除了處理棘手問題之外，其他事務不宜勉強推進。穩住就好。",
                "危日「不宜遠行買賣」（T21 p.397c-398a），涉及出差、大筆交易的事情建議延後。",
            ],
            "warning": [
                "業日「所作善惡亦不成就，甚衰」（T21 p.397c）。今天做什麼都難有結果，做好本分就好，不要主動爭取。需要談判或簽約的事延後。",
                "命日「不宜舉動百事」（T21 p.397c），今天不適合發起重要事務。靜守職位，把精力留給更好的時機。",
            ]
        },
        "love": {
            "excellent": [
                "親日「宜結交、定婚姻、歡宴聚會並吉」（T21 p.397c）。今天的人際互動特別順暢，適合約會、深入對話、確認關係。",
                "友日「宜結交朋友大吉」（T21 p.391b），社交場合容易認識到合得來的人。有伴的人一起吃頓飯、聊聊天就很好。",
                "栄日「對見大人」（T21 p.397c）的格局延伸到人際上，今天你的表達容易被對方接受。想說的話趁今天說。",
            ],
            "good": [
                "危日「宜結交、歡宴聚會並吉」（T21 p.397c），今天的聚餐、團聚氣氛不錯。自然地跟重要的人相處就好。",
                "安日「安坐臥床帳吉」（T21 p.397c），跟身邊人的日常相處今天很和諧。不需要大陣仗，安靜待在一起就舒服。",
                "品二各日吉凶（T21 p.397c-398a），今天人際互動中容易感受到善意，適合跟朋友聊聊近況、和家人吃頓飯。",
            ],
            "fair": [
                "安日「安坐臥床帳吉」（T21 p.397c），今日人際關係平穩，維持日常的關心和陪伴就好。不需要刻意經營也不會出問題。",
                "危日「宜結交、歡宴聚會並吉」（T21 p.397c），跟身邊人的互動尚可。想說什麼找個自然的時機表達就好。",
                "安危日級別（T21 p.397c-398a），感情面保持現狀即可，平淡也是一種安穩。",
            ],
            "caution": [
                "衰日「唯宜解除諸惡」（T21 p.398a），今天如果跟人有摩擦，專心解決問題而不是擴大衝突。說話前多想一下。",
                "壊日「餘並不堪」（T21 p.398a）在人際上也適用。今天不適合討論敏感話題或做關係中的重大決定。",
                "品二各日吉凶（T21 p.397c-398a），今天容易因小事產生誤解。先給彼此空間冷靜，不急著解釋。",
            ],
            "warning": [
                "業日「所作善惡亦不成就」（T21 p.397c），今天不管怎麼努力經營關係都不太見效。不如獨處充電，給自己和對方都留點空間。",
                "命日「不宜舉動百事」（T21 p.397c），今天不是告白、攤牌、或做關係重大決定的日子。忍一忍，好時機會來。",
            ]
        },
        "health": {
            "excellent": [
                "栄日（T21 p.397c）能量充沛，身體狀態處於高點。適合安排運動、戶外活動，體能表現比平時好。",
                "安日「安坐臥床帳吉」，身心安穩的一天。睡眠品質好，恢復力強，適合調整作息。",
                "成日「合和長年藥法」（T21 p.398a），今天適合開始健康計畫、調整飲食、建立運動習慣。",
            ],
            "good": [
                "友日「宜結交朋友大吉」（T21 p.391b），整體氣場順暢，身體沒什麼大問題。散步、伸展、輕鬆運動都好。",
                "友衰日級別（T21 p.397c-398a），精神狀態清醒，維持正常作息就好。天氣好的話出門走走對身心都有幫助。",
                "品二各日吉凶（T21 p.397c-398a），身體狀況穩定，適合延續既有的保健習慣。",
            ],
            "fair": [
                "安日「安坐臥床帳吉」（T21 p.397c），今日健康面平穩，維持日常保健就好。注意不要久坐，定時起來活動一下。",
                "安危日級別（T21 p.397c-398a），體能和精神在一般水準，按平時的作息走就好。",
                "危日有宜有忌（T21 p.397c-398a），沒有特別需要擔心的健康問題，保持現狀即可。",
            ],
            "caution": [
                "衰日「唯宜療病」（T21 p.398a），身體發出的訊號今天要認真對待。覺得不舒服就休息，不要硬撐。",
                "壊日「餘並不堪」（T21 p.398a），不適合高強度運動或過度消耗。省著點力氣用。",
                "品二各日吉凶（T21 p.397c-398a），今天容易感到疲勞，做幾次深呼吸、早點休息比什麼都管用。",
            ],
            "warning": [
                "業日「甚衰」（T21 p.397c），身體處於需要休養的狀態。避免熬夜和劇烈運動，早睡、多喝水是今天的重點。",
                "命日「不宜舉動百事」（T21 p.397c），今天給身體放個假。覺得不舒服就去看醫生，不要拖。",
            ]
        },
        "wealth": {
            "excellent": [
                "栄日「興營買賣」（T21 p.397c），今天的財務決策比平時準確。適合處理投資、簽約、談薪資。",
                "親日「定婚姻」（T21 p.397c）延伸到財務就是簽約吉。今天適合敲定合作條件、確認金額。",
                "栄日全面吉利（T21 p.397c），金錢方面的判斷可以信任。有好機會不要猶豫太久。",
            ],
            "good": [
                "成日「作諸成就法並吉」（T21 p.398a），財務規劃今天做起來特別順手。適合整理帳務、盤點資產。",
                "友日「宜結交朋友大吉」（T21 p.391b）人際互動帶動財運，合作機會、好的推薦今天比較容易出現。",
                "品二各日吉凶（T21 p.397c-398a），日常收支管理沒問題，正常消費不太會踩雷。",
            ],
            "fair": [
                "安日「造作園宅並吉」（T21 p.397c），財運平穩，維持平時的消費習慣即可。不需要刻意節省也不要衝動消費。",
                "危日「不宜買賣」但社交吉（T21 p.397c-398a），金錢方面中規中矩。大額支出的話可以再觀望一下。",
                "安危日級別（T21 p.397c-398a），處理日常帳單、繳費沒問題，但不建議今天做重大財務決策。",
            ],
            "caution": [
                "衰日「不宜買賣」（T21 p.398a），今天不適合大筆交易、投資決策。看到打折促銷先冷靜，想清楚再買。",
                "危日「不宜買賣」（T21 p.397c-398a），涉及金錢的談判今天效果不好。能拖幾天就拖幾天。",
                "壊日「餘並不堪」（T21 p.398a），財務面也是一樣。除了止損和處理問題，其他金錢決策延後。",
            ],
            "warning": [
                "業日「所作善惡亦不成就」（T21 p.397c），財運低迷。今天減少不必要的支出，簽約、投資、借貸全部延後。",
                "命日「不宜舉動百事」（T21 p.397c）包含財務面。今天不碰大錢最安全，日常小額消費就好。",
            ]
        }
    }

    # 凌犯期間專用描述（品三 p.391b-c「吉事皆凶、凶事皆吉」逆轉規則）
    # score >= 70: high_reversal（表吉實險 — 原典「吉事皆凶」）
    # 50-69: mid_reversal（局勢不明 — 吉凶交錯難判斷）
    # < 50: low_reversal（表凶有轉機 — 原典「凶事皆吉」）
    # 化解法：品三「宜入灌頂及護摩，並修諸功德」(p.391b)
    RYOUHAN_CATEGORY_DESCRIPTIONS = {
        "career": {
            "high_reversal": [
                {"zh": "品三記載凌犯期間「吉事皆凶」。工作表面順利，但這種順遂往往藏著陷阱。重要決策建議延後到凌犯結束，尤其是合約簽署和人事異動。",
                 "ja": "品三に凌犯期間は「吉事皆凶」と記載。仕事は表面上順調だが、この順調さには罠が潜む。重要な決断は凌犯終了後に延期すべし。"},
                {"zh": "凌犯期間「吉事皆凶」，看起來是好時機的事反而危險。今天做的決定可能幾天後翻盤，多觀察再行動。",
                 "ja": "凌犯期間「吉事皆凶」、好機に見えることほど危険。今日の決定が数日後に覆る可能性あり。様子を見てから行動すべし。"},
                {"zh": "品三「吉事皆凶」的格局。職場氣氛不錯但別被表象迷惑，原典建議「宜修諸功德」，靜心充實自己比主動出擊安全。",
                 "ja": "品三「吉事皆凶」の格局。職場の雰囲気は良いが表面に惑わされるな。原典は「宜しく諸の功徳を修すべし」と勧める。"},
            ],
            "mid_reversal": [
                {"zh": "凌犯期間吉凶難判斷，工作上的局勢不明朗。維持現有進度就好，品三建議「修諸功德」，把精力放在自我提升上。",
                 "ja": "凌犯期間は吉凶の判断が難しく、仕事の局面が不透明。現状維持に努め、品三の勧める「諸の功徳を修す」こと。"},
                {"zh": "凌犯影響下工作節奏不穩定，同事間容易誤解。溝通多確認一次，不要假設對方理解你的意思。",
                 "ja": "凌犯の影響で仕事のリズムが不安定。同僚間で誤解が生じやすい。コミュニケーションは確認を怠らないこと。"},
            ],
            "low_reversal": [
                {"zh": "品三「凶事皆吉」的格局。運勢雖低，但凌犯逆轉反而提供喘息空間。原本預期的阻礙可能沒那麼嚴重，不要急著放棄。",
                 "ja": "品三「凶事皆吉」の格局。運勢は低調だが、凌犯の逆転がかえって猶予を与える。予想された障害はそれほど深刻でない可能性あり。"},
                {"zh": "凌犯「凶事皆吉」，看似困難的處境可能暗藏轉機。先把手邊的事做好，品三說的「修諸功德」就是最好的準備。",
                 "ja": "凌犯「凶事皆吉」、困難に見える状況に転機が潜む可能性あり。手元の仕事をこなし、品三の「諸の功徳を修す」を実践すべし。"},
            ]
        },
        "love": {
            "high_reversal": [
                {"zh": "品三「吉事皆凶」，感情面看起來甜蜜的事反而要小心。今天的浪漫承諾和衝動告白，過幾天可能會覺得太冒進。",
                 "ja": "品三「吉事皆凶」、恋愛面で甘美に見えることほど注意。今日のロマンチックな約束や衝動的な告白は数日後に後悔する恐れあり。"},
                {"zh": "凌犯期間「吉事皆凶」，跟伴侶的互動表面和諧，但小問題可能在之後放大。心裡的話等凌犯過後再說比較好。",
                 "ja": "凌犯期間「吉事皆凶」、パートナーとの関係は表面上穏やかだが、小さな問題が後で拡大する恐れあり。本音の話し合いは凌犯後に。"},
            ],
            "mid_reversal": [
                {"zh": "凌犯期間感情判斷力模糊。對方的言行可能不是你想的那個意思，不要過度解讀，重大決定等凌犯結束再做。",
                 "ja": "凌犯期間は恋愛の判断力がぼやける。相手の言動を深読みせず、重大な決断は凌犯終了後に。"},
                {"zh": "凌犯影響下感情互動容易失準。今天維持日常相處就好，品三建議「修諸功德」，把時間花在充實自己上。",
                 "ja": "凌犯の影響で感情的やり取りにズレが生じやすい。日常の付き合いに留め、品三の勧める「諸の功徳を修す」を実践すべし。"},
            ],
            "low_reversal": [
                {"zh": "品三「凶事皆吉」，感情運雖低，但凌犯逆轉可能帶來意外的溫暖。之前冷淡的關係有回溫跡象，把握但不強求。",
                 "ja": "品三「凶事皆吉」、恋愛運は低調だが、凌犯の逆転が意外な温もりをもたらす可能性あり。冷えた関係に回復の兆し。"},
                {"zh": "凌犯「凶事皆吉」，看起來不順的感情反而有緩和的可能。保持平常心，不要因暫時低潮就做出分手的決定。",
                 "ja": "凌犯「凶事皆吉」、不調に見える恋愛にかえって緩和の可能性あり。平常心を保ち、一時の低迷で別れを決断しないこと。"},
            ]
        },
        "health": {
            "high_reversal": [
                {"zh": "品三「吉事皆凶」，身體感覺還行但容易忽視微弱警訊。不要做太激烈的運動，「覺得沒事」不代表真的沒問題。",
                 "ja": "品三「吉事皆凶」、体調は悪くないが微かな警告を見落としやすい。激しい運動は避け、不調を感じたら軽視しないこと。"},
                {"zh": "凌犯「吉事皆凶」，身體感知容易有偏差。飲食清淡一些、早點休息。品三建議「修諸功德」，讓身心都有恢復的餘裕。",
                 "ja": "凌犯「吉事皆凶」、体の感覚にズレが生じやすい。食事は控えめに、早めの休息を。品三の「諸の功徳を修す」で心身に回復の余裕を。"},
            ],
            "mid_reversal": [
                {"zh": "凌犯期間健康狀態不穩定，注意力和反應速度下降。開車、操作機具要比平常更小心。",
                 "ja": "凌犯期間は健康状態が不安定。注意力や反応速度が低下するため、運転や機械操作には普段以上の注意を。"},
                {"zh": "凌犯影響下身體狀況搖擺不定。不要臨時改變飲食或運動計畫，品三建議「修諸功德」，維持穩定作息最重要。",
                 "ja": "凌犯の影響で体調が揺れ動く。食事や運動の急な変更は避け、品三の「諸の功徳を修す」に従い安定した生活リズムの維持を。"},
            ],
            "low_reversal": [
                {"zh": "品三「凶事皆吉」，身體雖然偏弱，但凌犯逆轉可能讓慢性不適緩解。這是調養身體的好時機，順勢而為。",
                 "ja": "品三「凶事皆吉」、体調は弱めだが、凌犯の逆転で慢性的な不調が緩和される可能性あり。体を養う好機。"},
                {"zh": "凌犯「凶事皆吉」，健康面表面低迷但惡化風險不高。靜養休息、避免過勞，品三說的「修諸功德」就是最好的養生。",
                 "ja": "凌犯「凶事皆吉」、健康面は表面上低迷だが悪化のリスクは軽減。静養・休息に努め、品三の「諸の功徳を修す」が最良の養生。"},
            ]
        },
        "wealth": {
            "high_reversal": [
                {"zh": "品三「吉事皆凶」，財運看起來不錯但凌犯期間的「好運」常是錢來得快去得也快。獲利或好消息可能有隱藏成本。",
                 "ja": "品三「吉事皆凶」、金運は良さそうだが凌犯期間の「好運」は入りも出も速い。利益や良い知らせに隠れたコストがある可能性。"},
                {"zh": "凌犯「吉事皆凶」，表面的財運順遂要打折看待。投資、借貸、大額消費都等凌犯結束再評估。",
                 "ja": "凌犯「吉事皆凶」、表面的な金運の順調さは割り引いて見るべき。投資・借入・大きな支出は凌犯終了後に再評価を。"},
            ],
            "mid_reversal": [
                {"zh": "凌犯期間財務狀況不透明，收支可能有預期外的波動。今天適合整理帳目，不適合做財務決策。",
                 "ja": "凌犯期間中は財務状況が不透明で、収支に予想外の変動の可能性。帳簿の整理には適すが、財務的な決断には不向き。"},
                {"zh": "凌犯影響下金錢判斷力下降。看起來划算的東西可能有問題，購物前多比較。品三建議「修諸功德」，錢的事緩一緩。",
                 "ja": "凌犯の影響で金銭面の判断力が低下。お得に見えるものに問題が潜む可能性。品三の「諸の功徳を修す」に従い、金銭面は慎重に。"},
            ],
            "low_reversal": [
                {"zh": "品三「凶事皆吉」，財運偏弱但凌犯逆轉讓預期的損失可能不會發生。之前擔心的財務問題有緩解跡象，不必過度焦慮。",
                 "ja": "品三「凶事皆吉」、金運は弱めだが凌犯の逆転で予想された損失は回避できる可能性。財務問題に緩和の兆しあり。"},
                {"zh": "凌犯「凶事皆吉」，表面的財運低迷可能只是虛驚。守住現有資產，不要恐慌性地調整。",
                 "ja": "凌犯「凶事皆吉」、表面的な金運の低迷は杞憂に終わる可能性。現有資産を守り、パニック的な調整は控えるべし。"},
            ]
        }
    }

    # 甘露日/金剛峯日/羅刹日（宿曜經卷五）
    # key: (jp_weekday, day_mansion_index) → special_day_type
    # jp_weekday: 0=日, 1=月, 2=火, 3=水, 4=木, 5=金, 6=土
    SPECIAL_DAY_MAP = {
        # 甘露日（大吉）
        (0, 26): "kanro",   # 日曜 + 軫宿
        (1, 17): "kanro",   # 月曜 + 畢宿
        (2, 5): "kanro",    # 火曜 + 尾宿
        (3, 22): "kanro",   # 水曜 + 柳宿
        (4, 21): "kanro",   # 木曜 + 鬼宿
        (5, 3): "kanro",    # 金曜 + 房宿
        (6, 23): "kanro",   # 土曜 + 星宿
        # 金剛峯日（吉）
        (0, 5): "kongou",   # 日曜 + 尾宿
        (1, 4): "kongou",   # 月曜 + 心宿（大正藏底本，明版作女宿）
        (2, 12): "kongou",  # 火曜 + 壁宿
        (3, 16): "kongou",  # 水曜 + 昴宿
        (4, 20): "kongou",  # 木曜 + 井宿
        (5, 24): "kongou",  # 金曜 + 張宿
        (6, 1): "kongou",   # 土曜 + 亢宿
        # 羅刹日（凶）
        (0, 15): "rasetsu",  # 日曜 + 胃宿
        (1, 21): "rasetsu",  # 月曜 + 鬼宿
        (2, 25): "rasetsu",  # 火曜 + 翼宿
        (3, 19): "rasetsu",  # 水曜 + 参宿
        (4, 2): "rasetsu",   # 木曜 + 氐宿
        (5, 13): "rasetsu",  # 金曜 + 奎宿
        (6, 22): "rasetsu",  # 土曜 + 柳宿
    }

    SPECIAL_DAY_INFO = {
        "kanro": {
            "name": "甘露日",
            "reading": "かんろび",
            "level": "大吉",
            "description": "宿曜經記載的大吉日。原典記載「宜冊立、受灌頂法、造作寺宇及受戒、習學經法、出家修道，一切並吉」（T21 p.398b）。適合受灌頂、受戒、學道求法、造寺、出家修道、簽約、開業等重要行動。",
            "description_classic": "已上名甘露日，是大吉祥，宜冊立、受灌頂法、造作寺宇及受戒、習學經法、出家修道，一切並吉。（T21 p.398b）此等七日名為甘露吉祥日，宜學道求法，受密印及習真言。（T21 p.392c）",
            "description_ja": "甘露日は大吉祥の日なり。原典に「冊立・灌頂法を受け・寺宇を造作し・受戒・経法を習学し・出家修道に宜し、一切並びに吉」とある（T21 p.398b）。灌頂受法・受戒・学道求法・出家修道など最重要の仏事に最適なり。"
        },
        "kongou": {
            "name": "金剛峯日",
            "reading": "こんごうぶび",
            "level": "吉",
            "description": "宿曜經記載的吉日。原典記載「宜作一切降伏法，誦日天子呪及作護摩，並諸猛利等事」（T21 p.398b-c）。適合護摩修法、降伏法等猛利之行，以及面試、考試等需要毅力與持續力的行動。",
            "description_classic": "已上名金剛峯日，宜作一切降伏法，誦日天子呪及作護摩，並諸猛利等事。（T21 p.398b-c）此等七日名為金剛峯日，宜降伏魔怨，持日天子真言。（T21 p.392c）",
            "description_ja": "金剛峯日は吉日なり。原典に「一切の降伏法を作し、日天子呪を誦し、及び護摩を作し、並びに諸の猛利等の事に宜し」とある（T21 p.398b-c）。護摩修法・降伏法など猛利の行に最適なり。"
        },
        "rasetsu": {
            "name": "羅刹日",
            "reading": "らせつび",
            "level": "凶",
            "description": "宿曜經記載的凶日。原典記載「不宜舉百事，必有殃禍」（T21 p.398c），品五另記「不宜舉動百事，唯射獵及諸損害之事也」。避免一切重要行動。",
            "description_classic": "已上名羅刹日，不宜舉百事，必有殃禍。（T21 p.398c）右此等七日名為羅刹日，不宜舉動百事，唯射獵及諸損害之事也。（T21 p.392c）",
            "description_ja": "羅刹日は凶日なり。原典に「百事を挙ぐるに宜しからず、必ず殃禍あり」とある（T21 p.398c）。品五に「唯だ射獵及び諸の損害の事のみ」とあり、一切の重要行事を避くべし。"
        }
    }

    # 凌犯期間（七曜陵逼）查表
    # key: (農曆月, 朔日七曜) → (開始日, 結束日)
    # 農曆月: 1-12, 七曜: 0=日,1=月,2=火,3=水,4=木,5=金,6=土
    # 根據 nakshatra.tokyo 及宿曜經卷五
    RYOUHAN_MAP = {
        (1, 6): (1, 16),    # 正月 土曜 → 1-16日
        (1, 0): (17, 30),   # 正月 日曜 → 17-30日
        (2, 1): (1, 14),    # 二月 月曜 → 1-14日
        (2, 2): (15, 30),   # 二月 火曜 → 15-30日
        (3, 3): (1, 12),    # 三月 水曜 → 1-12日
        (3, 4): (13, 30),   # 三月 木曜 → 13-30日
        (4, 5): (1, 10),    # 四月 金曜 → 1-10日
        (4, 6): (11, 30),   # 四月 土曜 → 11-30日
        (5, 0): (1, 8),     # 五月 日曜 → 1-8日
        (5, 1): (9, 30),    # 五月 月曜 → 9-30日
        (6, 2): (1, 6),     # 六月 火曜 → 1-6日
        (6, 3): (7, 30),    # 六月 水曜 → 7-30日
        (7, 5): (1, 3),     # 七月 金曜 → 1-3日
        (7, 6): (4, 30),    # 七月 土曜 → 4-30日
        (8, 2): (1, 27),    # 八月 火曜 → 1-27日
        (9, 4): (1, 25),    # 九月 木曜 → 1-25日
        (9, 5): (26, 30),   # 九月 金曜 → 26-30日
        (10, 6): (1, 23),   # 十月 土曜 → 1-23日
        (10, 0): (24, 30),  # 十月 日曜 → 24-30日
        (11, 2): (1, 20),   # 十一月 火曜 → 1-20日
        (11, 3): (21, 30),  # 十一月 水曜 → 21-30日
        (12, 4): (1, 18),   # 十二月 木曜 → 1-18日
        (12, 5): (19, 30),  # 十二月 金曜 → 19-30日
    }

    # 凌犯期間三語描述（編者歸納，據品五凌犯月別配當表, T21 p.392a-b；nakshatra.tokyo 交叉驗證）
    RYOUHAN_DESCRIPTIONS = {
        1: {
            "classic": "正月土曜朔，初一至十六日陵逼。日曜朔，十七至三十日陵逼。",
            "ja": "正月の朔日が土曜なら1日〜16日、日曜なら17日〜30日が凌犯期間となる。",
            "zh": "正月朔日為土曜時，初一至十六為凌犯期間；朔日為日曜時，十七至三十為凌犯期間。"
        },
        2: {
            "classic": "二月月曜朔，初一至十四日陵逼。火曜朔，十五至三十日陵逼。",
            "ja": "二月の朔日が月曜なら1日〜14日、火曜なら15日〜30日が凌犯期間となる。",
            "zh": "二月朔日為月曜時，初一至十四為凌犯期間；朔日為火曜時，十五至三十為凌犯期間。"
        },
        3: {
            "classic": "三月水曜朔，初一至十二日陵逼。木曜朔，十三至三十日陵逼。",
            "ja": "三月の朔日が水曜なら1日〜12日、木曜なら13日〜30日が凌犯期間となる。",
            "zh": "三月朔日為水曜時，初一至十二為凌犯期間；朔日為木曜時，十三至三十為凌犯期間。"
        },
        4: {
            "classic": "四月金曜朔，初一至十日陵逼。土曜朔，十一至三十日陵逼。",
            "ja": "四月の朔日が金曜なら1日〜10日、土曜なら11日〜30日が凌犯期間となる。",
            "zh": "四月朔日為金曜時，初一至十為凌犯期間；朔日為土曜時，十一至三十為凌犯期間。"
        },
        5: {
            "classic": "五月日曜朔，初一至八日陵逼。月曜朔，九至三十日陵逼。",
            "ja": "五月の朔日が日曜なら1日〜8日、月曜なら9日〜30日が凌犯期間となる。",
            "zh": "五月朔日為日曜時，初一至八為凌犯期間；朔日為月曜時，九至三十為凌犯期間。"
        },
        6: {
            "classic": "六月火曜朔，初一至六日陵逼。水曜朔，七至三十日陵逼。",
            "ja": "六月の朔日が火曜なら1日〜6日、水曜なら7日〜30日が凌犯期間となる。",
            "zh": "六月朔日為火曜時，初一至六為凌犯期間；朔日為水曜時，七至三十為凌犯期間。"
        },
        7: {
            "classic": "七月金曜朔，初一至三日陵逼。土曜朔，四至三十日陵逼。",
            "ja": "七月の朔日が金曜なら1日〜3日、土曜なら4日〜30日が凌犯期間となる。",
            "zh": "七月朔日為金曜時，初一至三為凌犯期間；朔日為土曜時，四至三十為凌犯期間。"
        },
        8: {
            "classic": "八月火曜朔，初一至二十七日陵逼。",
            "ja": "八月の朔日が火曜なら1日〜27日が凌犯期間となる。",
            "zh": "八月朔日為火曜時，初一至二十七為凌犯期間。"
        },
        9: {
            "classic": "九月木曜朔，初一至二十五日陵逼。金曜朔，二十六至三十日陵逼。",
            "ja": "九月の朔日が木曜なら1日〜25日、金曜なら26日〜30日が凌犯期間となる。",
            "zh": "九月朔日為木曜時，初一至二十五為凌犯期間；朔日為金曜時，二十六至三十為凌犯期間。"
        },
        10: {
            "classic": "十月土曜朔，初一至二十三日陵逼。日曜朔，二十四至三十日陵逼。",
            "ja": "十月の朔日が土曜なら1日〜23日、日曜なら24日〜30日が凌犯期間となる。",
            "zh": "十月朔日為土曜時，初一至二十三為凌犯期間；朔日為日曜時，二十四至三十為凌犯期間。"
        },
        11: {
            "classic": "十一月火曜朔，初一至二十日陵逼。水曜朔，二十一至三十日陵逼。",
            "ja": "十一月の朔日が火曜なら1日〜20日、水曜なら21日〜30日が凌犯期間となる。",
            "zh": "十一月朔日為火曜時，初一至二十為凌犯期間；朔日為水曜時，二十一至三十為凌犯期間。"
        },
        12: {
            "classic": "十二月木曜朔，初一至十八日陵逼。金曜朔，十九至三十日陵逼。",
            "ja": "十二月の朔日が木曜なら1日〜18日、金曜なら19日〜30日が凌犯期間となる。",
            "zh": "十二月朔日為木曜時，初一至十八為凌犯期間；朔日為金曜時，十九至三十為凌犯期間。"
        },
    }

    # 六害宿：凌犯期間中以本命宿為基準的 6 個大凶日宿
    # 順時計方向（宿曜盤上順行）偏移量
    # 來源：yakumoin.net, kosei-do.co.jp, sukuyou.divination.page 三方交叉驗證
    # 凶度排序：命宿 > 事宿 > 意宿 > 聚宿 > 同宿 > 克宿
    ROKUGAI_OFFSETS = {
        "命宿": {"offset": 0, "severity": 1, "reading": "めいしゅく"},   # 本命宿
        "意宿": {"offset": 3, "severity": 3, "reading": "いしゅく"},   # 一九の安（第 4 番目）
        "事宿": {"offset": 9, "severity": 2, "reading": "じしゅく"},   # 業（第 10 番目）
        "克宿": {"offset": 12, "severity": 6, "reading": "こくしゅく"},  # 二九の安（第 13 番目）
        "聚宿": {"offset": 15, "severity": 4, "reading": "じゅしゅく"},  # 二九の壊（第 16 番目）
        "同宿": {"offset": 19, "severity": 5, "reading": "どうしゅく"},  # 三九の栄（第 20 番目）
    }

    # 三期サイクル：27 日為一循環，分三期各 9 天
    # 每期的起始關係和名稱
    SANKI_CYCLE = [
        {"name": "躍動の週", "reading": "やくどうのしゅう", "start_relation": "命",
         "description": "活動期（三九秘法，T21 品二 p.397c-398a）。27日循環的第一期（一九），從命宿開始。能量充沛，適合積極行動、開展新事。",
         "description_classic": "（編者歸納）一九者，命宿起行之期。命日「不宜舉動百事」、栄日「及諸吉事並大吉」、安日「移徙吉，遠行人入宅、造作園宅、安坐臥床帳、作壇場並吉」、成日「宜修道學問、合和長年藥法，作諸成就法並吉」、友・親日「宜結交、定婚姻，歡宴聚會並吉」（T21 p.397c-398a）。",
         "description_ja": "一九（いっく）は命宿から始まる活動期なり（三九秘法、T21 品二 p.397c-398a）。27日循環の最初の9日間にして、エネルギーが最も充実する時期。新たな計画の発起、重要な約束、積極的な行動に適す。"},
        {"name": "破壊の週", "reading": "はかいのしゅう", "start_relation": "業",
         "description": "衰退期（三九秘法，T21 品二 p.397c-398a）。27日循環的第二期（二九），從業宿開始。前期積累的問題浮現，宜收斂整理。",
         "description_classic": "（編者歸納）二九者，業宿起行之期。原典記載「值業宿日，所作善惡亦不成就，甚衰」（T21 p.397c）。",
         "description_ja": "二九（にく）は業宿から始まる衰退期なり（三九秘法、T21 品二 p.397c-398a）。前期に蓄積した疲労や問題が表面化し、エネルギーが収斂に向かう。新規の着手を避け、手元の整理と反省に努めるべき時期。"},
        {"name": "再生の週", "reading": "さいせいのしゅう", "start_relation": "胎",
         "description": "轉換期（三九秘法，T21 品二 p.397c-398a）。27日循環的第三期（三九），從胎宿開始。舊的結束、新的萌芽，適合反省與準備。",
         "description_classic": "（編者歸納）三九者，胎宿起行之期。原典記載「凡命、胎宿直日，不宜舉動百事」（T21 p.391b）。",
         "description_ja": "三九（さんく）は胎宿から始まる転換期なり（三九秘法、T21 品二 p.397c-398a）。27日循環の最終段階にして、古きものの終わりと新しきものの萌芽が同時に起こる。静養・整理・準備に充て、次の循環に向けた蓄力の時期とす。"},
    ]

    # 三期サイクル各日型（每期 9 天：起始日 + 栄→衰→安→危→成→壊→友→親）
    # 起始日因期而異：一九=命、二九=業、三九=胎
    SANKI_DAY_TYPES = {
        # 各期的第 1 天（起始日）
        "period_start": {
            1: {"name": "命の日", "reading": "めいのひ",
                "description": "27 日循環的起點，本命宿回歸之日。原典記載「凡命、胎宿直日，不宜舉動百事」（T21 p.391b; p.397c），應靜守本分，不宜開展新事或做重大決定。適合反省與沉澱。",
                "description_ja": "27 日循環の起点にして本命宿回帰の日。原典に「凡そ命・胎の宿の直日は、百事を挙動するに宜しからず」（T21 p.391b; p.397c）とあり、新規の着手や重大な決断を避け、静かに自省するのが良い。"},
            2: {"name": "業の日", "reading": "ごうのひ",
                # 校勘注：品三(p.391b)記載「業宿直日，所作皆吉祥」，卷下(p.397c)記載「所作善惡亦不成就，甚衰」。
                # 兩處記載矛盾，系統採用卷下版本（三九秘要法的詳細展開，更具體可操作）。
                "description": "前世因緣顯現的業之位置。原典卷下記載「所作善惡亦不成就，甚衰」（注：品三另記「所作皆吉祥」，兩說不同，系統從卷下）。做什麼都難有結果，應低調收斂，不宜妄動。破壊の週的入口。",
                "description_ja": "前世からの因縁を示す業の位置。原典巻下に「善悪ともに成就せず、甚だ衰なり」とある（注：品三には「所作皆吉祥」とあり記載が異なる。本システムは巻下に従う）。何をしても結果に繋がりにくい。控えめに過ごし、破壊の週の入口として心構えを整える日。"},
            3: {"name": "胎の日", "reading": "たいのひ",
                "description": "再生的開始，對應胎之位置。原典記載「凡命、胎宿直日，不宜舉動百事」（T21 p.391b; p.397c），與命日同為靜守之日。適合靜心內省，為下一個循環做準備。",
                "description_ja": "再生の始まりにして胎の位置。原典に「凡そ命・胎の宿の直日は、百事を挙動するに宜しからず」（T21 p.391b; p.397c）とあり、命の日と同じく静守の日。内省を深め、次の循環に備える時。"},
        },
        # 第 2-9 天（全期共通）
        "day": {
            2: {"name": "栄の日", "reading": "えいのひ",
                "description": "原典卷下記載「即宜入官拜職、對見大人、上書表進獻君王、興營買賣、裁著新衣、沐浴及諸吉事並大吉。出家人剃髮、割爪甲、沐浴、承事師主、啟請法要並吉」（T21 p.397c-398a）。積極行動的好日子。",
                "description_ja": "原典に「諸の吉事並びに大吉なり」とある。官職拝命・大人への拝謁・上書表の進献・売買経営・新衣を裁著し・沐浴及び諸の吉事並びに大吉。出家者の剃髪・爪切り・沐浴・師事・法要請願並びに吉。積極的に動いて吉。"},
            3: {"name": "衰の日", "reading": "すいのひ",
                "description": "原典卷下記載「唯宜解除諸惡、療病」（T21 p.398a），品三另記「並不宜遠行，出入遷移、買賣裁衣、剃頭剪甲並不吉」（T21 p.391b）。氣勢減弱，適合除障、破邪、療病等淨化性質的行為，其餘不宜勉強。",
                "description_ja": "原典に「唯だ諸悪を解除し、病を療するに宜し」とあり、「遠行・出入遷移・売買・裁衣・剃頭剪甲並びに不吉」とも。気勢は弱まるが、浄化の行には向く。それ以外は無理をしないこと。"},
            4: {"name": "安の日", "reading": "あんのひ",
                "description": "原典卷下記載「移徙吉，遠行人入宅、造作園宅、安坐臥床帳、作壇場並吉」（T21 p.397c-398a，品三作「移動遠行、修園宅臥具、作壇場並吉」）。穩定安寧之日，搬遷、遠行歸宅、造宅、設壇修法皆吉。踏實前行的好時機。",
                "description_ja": "原典に「移徙吉、遠行人の入宅、園宅を造作し、坐臥の床帳を安んじ、壇場を作るに並びに吉」とある。安定の気が流れ、引越し・遠方からの帰宅・建築・寝具の設え・壇場設営に好適。着実に進めるのが吉。"},
            5: {"name": "危の日", "reading": "きのひ",
                "description": "原典卷下記載「宜結交、定婚姻，歡宴聚會並吉」（T21 p.397c-398a），但另記「危壞日，並不宜遠行出、入移徙、買賣、婚姻、裁衣、剃頭、沐浴並凶」（T21 p.398a）（注：婚姻在兩處記載吉凶不同）。社交聚會吉，遠行買賣則宜避開。",
                "description_ja": "原典に「結交を宜し、婚姻を定め、歓宴聚会並びに吉」とある一方、「危壞日は並びに遠行出・入移徙・売買・婚姻・裁衣・剃頭・沐浴に宜しからず並びに凶」とも（注：婚姻の吉凶が箇所により異なる）。社交は吉、遠行・売買は避けるのが良い。"},
            6: {"name": "成の日", "reading": "せいのひ",
                "description": "原典卷下記載「宜修道學問、合和長年藥法，作諸成就法並吉」（T21 p.398a，品三作「修學問道、合藥求仙吉」）。修法、學問、成就法皆吉。努力的成果開花結果，適合修行精進和完成重要事項。",
                "description_ja": "原典に「修道学問に宜し、長年の薬法を合和し、諸の成就法を作すに並びに吉」とある。修法・学問・合薬・成就法すべてに好適。努力が実を結び、修行精進と重要事項の完遂に最適。"},
            7: {"name": "壊の日", "reading": "かいのひ",
                "description": "原典卷下記載「宜作鎮壓、降伏怨讎及討伐阻壞奸惡之謀，餘並不堪」（T21 p.398a，品三作「又宜壓鎮降伏怨讎及討伐暴惡」）。另「危壞日，並不宜遠行出、入移徙、買賣、婚姻、裁衣、剃頭、沐浴並凶」。降伏法和鎮壓可行，但其他事務不宜。具有破邪顯正的力量。",
                "description_ja": "原典に「鎮圧を作し、怨讐を降伏し、阻壞奸悪の謀を討伐するに宜し、余は並びに堪えず」とある。降伏法・鎮圧・討伐は可能だが、他の事には不向き。破邪顕正の力がある日。"},
            8: {"name": "友の日", "reading": "ゆうのひ",
                "description": "原典品三記載「宜結交朋友大吉」（T21 p.391b），卷下記載「宜結交、定婚姻，歡宴聚會並吉」（T21 p.397c-398a）。人際關係圓滑，適合社交、宴會和協作。",
                "description_ja": "原典品三に「朋友と結交するに大吉」、巻下に「結交を宜し、婚姻を定め、歓宴聚会に並びに吉」とある。人間関係が円滑に進み、社交・宴席・共同作業に好適。"},
            9: {"name": "親の日", "reading": "しんのひ",
                "description": "原典品三記載「宜結交朋友大吉」，卷下記載「宜結交、定婚姻，歡宴聚會並吉」（與友日記載相同）。適合與家人、伴侶、至交相聚，社交宴會吉。",
                "description_ja": "原典に「結交を宜し、婚姻を定め、歓宴聚会に並びに吉」とある（友日と同じ記載）。家族・恋人・親しい友人との集まりに好適。社交・宴席に吉。"},
        }
    }

    # 月運勢專用描述（以 T21n1299 品二各日吉凶為基礎）
    # 月運用六關係判定，經文依據同日運
    MONTHLY_FORTUNE_DESCRIPTIONS = {
        # 栄「宜入官拜職、對見大人、上書表進獻君王、興營買賣」(p.397c)
        # 親「宜結交、定婚姻、歡宴聚會並吉」(p.397c)
        "eishin": [
            "原典記載栄日「宜入官拜職、對見大人」，親日「宜結交、歡宴聚會並吉」（T21 p.397c）。本月與本命宿形成栄親關係，適合推動重要計畫、拓展人脈、爭取升遷機會。",
            "栄日「宜興營買賣」（T21 p.397c），本月適合推進業務、簽約、談合作。如果有拖著沒做的提案，這個月送出去的成功率高。",
            "親日「宜結交、定婚姻」（T21 p.397c），本月人際互動順暢。面試、社交場合、建立長期合作關係都是好時機。",
            "栄日「上書表進獻君王」（T21 p.397c），本月提案、報告、建議容易被接受。想向上級爭取什麼，安排在這個月效果最好。",
            "栄親月全面吉利。原典明記多項大吉事宜，不管是職場表現還是人際拓展，積極行動會有回報。"
        ],
        # 業「所作善惡亦不成就、甚衰」(p.397c)
        # 胎「不宜舉動百事」(p.397c) + 「宜修功德」(品三 p.391b)
        "gyotai": [
            "原典記載業日「所作善惡亦不成就，甚衰」，胎日「不宜舉動百事」（T21 p.397c）。本月與本命宿形成業胎關係，不管做什麼都不容易有結果，最好的策略是收斂觀望。",
            "業日「甚衰」（T21 p.397c），本月的運勢在低點。不適合啟動新計畫、跳槽、談判或大額投資，把精力放在維持現狀上。",
            "胎日「不宜舉動百事」（T21 p.397c），本月不是起頭的月份。想做的新事情先規劃、先調查，等下個月再動手。",
            "品三記載「宜修功德」（T21 p.391b），雖然對外行動不利，但適合向內充實：進修、讀書、整理思路，為之後的行動蓄力。",
            "品二業胎（T21 p.397c「不成就」），業胎月勉強推進反而消耗更多。接受這個月的節奏，把該整理的整理好、該學的學好，下一波栄親月你就能全力衝刺。"
        ],
        # 命「不宜舉動百事」(p.397c) + 「宜修功德」(品三 p.391b)
        "mei": [
            "原典記載命日「不宜舉動百事」（T21 p.397c）。本月本命宿回歸，適合靜守本分，不宜主動發起重要事務。",
            "命日「不宜舉動」（T21 p.397c），本月不爭不搶最安全。把精力放在自我檢視、盤點資源上，比對外衝刺更實際。",
            "品三記載命日「宜修功德」（T21 p.391b），本月適合自我充實：進修、反省、規劃未來方向，安靜地為下一步做準備。",
            "命月（T21 p.397c「不宜舉動百事」）不適合做重大決定。如果有人催你表態或簽約，能緩就緩，不是逃避而是時機不對。",
            "本命宿月（T21 p.397c）適合面對自己。最近的工作方向對不對、生活重心需不需要調整，趁這個月靜下來想清楚。"
        ],
        # 友「宜結交朋友大吉、歡宴聚會並吉」(p.397c, p.391b)
        # 衰「唯宜解除諸惡、療病」「不宜出入遷移、買賣」(p.398a, p.391b)
        "yusui": [
            "原典記載友日「宜結交朋友大吉」，衰日「唯宜解除諸惡、療病」「不宜出入遷移、買賣」（T21 p.397c-398a）。社交聚會吉，但不適合搬遷、轉職、大筆交易。",
            "友日「宜結交朋友大吉」（T21 p.391b），本月的人際互動順暢，聚餐、聯繫人脈、拓展社交圈都好。",
            "衰日「唯宜解除諸惡、療病」（T21 p.398a），本月適合處理累積的問題和待辦事項，把拖著沒解決的清掉。",
            "衰日「不宜出入遷移、買賣」（T21 p.398a），本月不是搬家、跳槽、做大筆投資的好時機。能延後就延後。",
            "友衰月（T21 p.397c-398a）的節奏：對人好、對事慢。多跟人互動、維護關係，但工作上維持現狀，不做大動作。"
        ],
        # 危「宜結交、歡宴聚會並吉」「不宜遠行出入移徙、買賣」(p.397c, p.398a)
        # 成「宜修道學問、合和長年藥法、作諸成就法並吉」(p.398a)
        "kisei": [
            "原典記載危日「宜結交、歡宴聚會並吉」「不宜遠行買賣」，成日「宜修道學問、作諸成就法並吉」（T21 p.397c-398a）。社交和學習吉，出差和大額交易不宜。",
            "成日「宜修道學問」（T21 p.398a），本月特別適合進修、考取證照、學習新技能，專注力和理解力處於佳狀態。",
            "危日「宜結交、歡宴聚會並吉」（T21 p.397c），本月的聚餐、聯誼、業界交流容易有收穫。",
            "危日「不宜遠行出入移徙、買賣」（T21 p.398a），涉及出差、搬遷、大筆交易的事情建議排到下個月。",
            "成日「作諸成就法並吉」（T21 p.398a），正在進行中的專案本月適合收尾。在學的東西容易融會貫通，把握這個月精進。"
        ],
        # 安「移徙吉、遠行人入宅、造作園宅、作壇場並吉」(p.397c)
        # 壊「宜作鎮壓、降伏怨讎、餘並不堪」(p.398a)
        "ankai": [
            "原典記載安日「移徙吉、造作園宅」，壊日「宜作鎮壓、降伏怨讎，餘並不堪」（T21 p.397c-398a）。安頓環境吉，處理棘手問題可行，其餘事不宜勉強。",
            "安日「移徙吉」（T21 p.397c），本月如果有搬遷、轉調、整理環境的需求，放手去做，安頓的事做起來順。",
            "壊日「宜作鎮壓、降伏怨讎」（T21 p.398a），本月有棘手問題或難纏的對手，正面處理反而能見效。但「餘並不堪」，其他事不要硬推。",
            "安日「造作園宅、作壇場並吉」（T21 p.397c），本月適合建立新制度、整理工作流程、把環境和基礎打好。",
            "壊日「餘並不堪」（T21 p.398a），除了處理棘手問題之外，重大事務建議延後。不是能力問題，是時機不支持。"
        ]
    }

    # 月運勢建議（以 T21n1299 品二各日宜忌為基礎）
    MONTHLY_FORTUNE_ADVICE = {
        # 栄「宜入官拜職、興營買賣」親「宜結交、歡宴聚會」(p.397c)
        "eishin": [
            "栄日「宜入官拜職」（T21 p.397c），本月把最重要的爭取排上去：升遷、面試、提案、談合作。行動會有回報。",
            "親日「宜結交」（T21 p.397c），有想認識的人就主動聯繫、有想合作的對象就約見面。本月開口的成功率高。",
            "栄日「興營買賣」（T21 p.397c），本月的業務推進、簽約談判效率比平時好，該推的案子趁這個月推。",
            "栄日「上書表進獻君王」（T21 p.397c），把準備好的報告、企劃書送出去。本月提案容易被採納。",
            "栄親月全面吉利（T21 p.397c），把最重要的事排在這個月處理，效率和結果都在高點。"
        ],
        # 業「所作善惡亦不成就」胎「不宜舉動百事」(p.397c) + 「宜修功德」(品三 p.391b)
        "gyotai": [
            "業日「所作不成就」（T21 p.397c），本月不是對外爭取的月份。收斂等待，把力氣留給下一波。",
            "胎日「不宜舉動百事」（T21 p.397c），想做的新計畫先規劃到紙上，等下個月再啟動。",
            "品三「宜修功德」（T21 p.391b），本月適合進修、讀書、學新技能。對內充實比對外衝刺有效。",
            "業胎月（品二 T21 p.397c「所作善惡亦不成就」）強行推進反而消耗更多。把該整理的整理好，下一波栄親月你就能全力出發。",
            "品二業胎（T21 p.397c「不成就」），接受這個月的低調節奏。累積實力的過程不顯眼，但之後會用得上。"
        ],
        # 命「不宜舉動百事」(p.397c) + 「宜修功德」(品三 p.391b)
        "mei": [
            "命日「不宜舉動百事」（T21 p.397c），本月給自己獨處的時間，好好整理思緒，為未來做準備。",
            "品三「宜修功德」，回顧過去幾個月做的事情，哪些值得繼續、哪些該調整，趁現在想清楚。",
            "品二命日（T21 p.397c「不宜舉動百事」），本月不適合做重大決定。如果有人催你表態，先緩一緩再回覆。",
            "命月（T21 p.397c「不宜舉動百事」）適合定下來想想你真正在乎的事。工作、生活、關係，排個優先順序，之後行動更有方向。",
            "品三「宜修功德」（T21 p.391b），不需要急著有進展。靜守的月份把內功練好，比急著出招更實在。"
        ],
        # 友「宜結交朋友大吉」衰「唯宜解除諸惡、不宜買賣」(p.397c-398a)
        "yusui": [
            "友日「宜結交朋友大吉」（T21 p.391b），本月把注意力放在經營人際關係上，聚餐、聯繫舊友都好。",
            "衰日「唯宜解除諸惡」（T21 p.398a），拖了很久沒處理的問題和雜務，趁這個月清掉。",
            "衰日「不宜買賣」（T21 p.398a），大筆交易和投資延後。穩穩守住現有的，不急於求成。",
            "友衰月的策略（品二 T21 p.397c-398a）：社交圈可以拓展，但業務和財務上維持現狀就好。",
            "品二各日吉凶（T21 p.397c-398a），每一天把該做的事做好，累積下來比急著衝刺更扎實。"
        ],
        # 危「宜結交、不宜遠行買賣」成「宜修道學問」(p.397c-398a)
        "kisei": [
            "成日「宜修道學問」（T21 p.398a），本月做決定前多留一天冷靜期，急著回覆反而容易後悔。",
            "危日「不宜遠行買賣」（T21 p.398a），涉及出差、大筆交易的事情需要格外謹慎。",
            "成日「作諸成就法並吉」（T21 p.398a），備份重要檔案、確認截止日期、提前處理行政事務，避開問題比事後補救好。",
            "危日「宜結交、歡宴聚會」（T21 p.397c），跟人合作的時候把責任講清楚，白紙黑字比口頭約定可靠。",
            "危成月（T21 p.397c-398a）半吉半忌，學習和社交方面放心去做，金錢和遷移方面小心處理。"
        ],
        # 安「移徙吉、造作園宅」壊「餘並不堪」(p.397c-398a)
        "ankai": [
            "壊日「餘並不堪」（T21 p.398a），本月保持低調，養精蓄銳，等更好的時機再出擊。",
            "安日「移徙吉」（T21 p.397c），如果有整頓環境、調整基礎設施的需求，這個月做得順。",
            "壊日的正面用法：「宜作鎮壓、降伏怨讎」（T21 p.398a）。有棘手問題就正面處理，但其他新事物不要碰。",
            "品二安壊日（T21 p.397c-398a），本月少做承諾、少接新任務，把現有的事情收好收滿就夠了。等運勢轉好再擴張。",
            "安壊月（T21 p.397c-398a）的策略：安頓的事放心做，拓展的事先等等。守好現有的，時機到了自然能動。"
        ]
    }

    # 週運焦點（基於 T21n1299 品八七曜五行體系）
    # 宿曜經以七曜各主一元素為運算基礎，本命元素與當週主曜元素的五行關係決定週運基調
    WEEKLY_FORTUNE_FOCUS = {
        # 同元素：七曜主曜與本命同屬一元素，能量共振
        "same": [
            "本週主曜與本命同屬一元素（基於品八七曜五行，T21 p.399a）。同元素共振期間，判斷力和執行力處於高峰，適合推進需要專注力的重要工作。把關鍵決策和會議安排在這幾天。",
            "七曜五行同屬的一週，你和環境的節奏對上了。平時覺得吃力的事這週會變輕鬆，溝通理解力也比平時好。適合處理需要深度思考的任務。",
            "七曜五行同元素週讓你的個人特質更鮮明，擅長的領域表現突出。適合做簡報、帶領團隊、處理需要說服力的事。",
            "七曜同元素共振，你的表達力和影響力都在高位。這週做出的決定通常經得起時間考驗。",
            "七曜五行同元素週，本週你的存在感比平時強。不管是職場發言還是生活互動，別人會更關注你的想法。利用這份影響力推動你在意的事。"
        ],
        # 相生：五行相生（木生火、火生土、土生金、金生水、水生木），外在滋養本命
        "generating": [
            "本週主曜元素與本命形成五行相生（基於品八七曜五行，T21 p.399a）。外在能量滋養本命，環境條件有利。別人的支持和配合比平時容易到位，適合處理需要外部資源的事。",
            "品八七曜五行相生週，人際互動中容易獲得協助，工作阻力也比預期小。把拖延已久的重要事項排進行程，本週推進效率高。",
            "品八七曜五行相生能量讓學新東西的吸收力強、推動計畫的執行力好。如果有想研究的題目，這週花幾個晚上好好鑽研。",
            "品八七曜五行相生，外部資源向你匯聚的一週。同事的協助、朋友的資訊、工作中的捷徑，你會覺得身邊的人和事都在幫你。放大行動範圍，多跨出一步。",
            "品八七曜五行相生帶來的學習效率特別高。讀書、上課、邊做邊學，你能比平時更快地把新知識轉化為可用的能力。"
        ],
        # 相洩：本命生外在（木生火時木被洩），能量外流
        "weakening": [
            "本週本命元素生外在主曜元素（品八七曜五行相洩，T21 p.399a），能量有向外流失的跡象。調整節奏最重要：減少不必要的社交，把精力集中在少數幾件真正重要的事上。做得少但做得好，比什麼都碰更有價值。",
            "品八七曜五行相洩的一週，動力可能不如上週。正常的週期變化，降低同時處理的事情數量。把待辦清單砍掉一半，專心把剩下的做好。同時注意飲食和睡眠。",
            "品八七曜五行相洩，本週適合用效率取代時間。不要加班補進度，優化流程才是對策。能委託的委託、能簡化的簡化，省下的精力留給關鍵環節。",
            "品八七曜五行相洩，消耗感比較明顯的一週。身體在暗示你放慢速度。中午能小睡就小睡，晚上能早一小時上床就早一小時。體力恢復直接影響下週表現。",
            "品八七曜五行相洩，本週不適合同時處理太多事。列出待辦後，前三名以外的全部延到下週。精力有限，三件事做到九十分比十件事做到五十分好。"
        ],
        # 相剋：五行相剋（木剋土、土剋水、水剋火、火剋金、金剋木），外在壓制本命
        "conflicting": [
            "本週主曜元素與本命形成五行相剋（基於品八七曜五行）。計畫可能遇到預期外的變數。遇到卡關先退一步看全局，找到問題的真正原因再處理，比硬推有效。本週耐心比能力重要。",
            "品八七曜五行相剋週的挑戰在於控制節奏。外在干擾讓你想加快速度，但越急越容易出錯。每天完成最重要的三件事就好，其他留到下週。",
            "品八七曜五行相剋，溝通方面本週需要多花心思。別人的反應可能不如預期，不是你說錯了什麼，而是雙方頻率暫時沒對上。重要訊息用文字確認。",
            "品八七曜五行相剋，這週可能出現措手不及的狀況。提前把重要任務截止日往前拉兩天，留緩衝空間。萬一遇到突發，還有時間應對。",
            "品八七曜五行相剋帶來的張力不全是壓力，有時是突破的契機。卡住的問題在摩擦中反而可能逼出新解法。換個角度看問題。"
        ],
        # 中性：本命與主曜無直接生剋關係
        "neutral": [
            "本週主曜元素與本命無直接生剋關係（品八七曜五行，T21 p.399a），能量平穩。這種時候你的主動作為最重要——想推什麼就去推、想學什麼就去學。踏實做事，結果不會讓你失望。",
            "七曜五行中性能量的一週，適合處理需要穩定輸出的工作。寫報告、整理資料、複習進度，這些不太刺激但重要的事在這週做最恰當。",
            "七曜五行中性週，外在環境不會推你也不會拉你，自己決定這週的重點。挑一件最想完成的事，集中火力去做。沒有干擾的時候，專注力是最強的武器。",
            "七曜五行中性，平穩的一週適合做規劃。下個月的計畫、年度目標的進度檢查，在沒有外力干擾的時候做規劃，頭腦最清楚。",
            "七曜五行中性，本週不會有什麼意外打亂節奏。利用穩定期把雜事清一清——回覆積壓的訊息、整理資料、確認待辦。把小石頭搬開，後面跑起來更順。"
        ]
    }

    # 週運各項提示（基於 T21n1299 品八七曜五行體系）
    # 事業/感情/健康的週度短提示，依五行相性分類
    WEEKLY_CATEGORY_TIPS = {
        "career": {
            # 同元素：七曜與本命同屬，能量共振
            "same": [
                "七曜同元素週，事業上判斷力穩定。適合做重要決策、推進需要個人擔當的專案。",
                "工作效率高峰期。把最需要專注力的任務排在這幾天，產出品質處於最佳狀態。"
            ],
            # 相生：外在滋養本命
            "generating": [
                "品八七曜五行相生週，職場上容易獲得支援。需要主管點頭的提案，趁這幾天提出來，通過率較高。",
                "品八七曜五行相生週，團隊協作的效率本週好。提案容易被接受，配合度高。把需要多方溝通的任務排在這週。"
            ],
            # 相洩：能量外流
            "weakening": [
                "品八七曜五行相洩週，事業上以守為主。適合把現有工作做到更好：優化流程、整理文件、復盤成果。",
                "品八七曜五行相洩週，工作量可能比預期大，優先處理有截止日的任務。非緊急事項留到下週，精力有限用在刀口上。"
            ],
            # 相剋：外在壓制本命
            "conflicting": [
                "品八七曜五行相剋週，職場溝通注意措辭。重要指示和協議用文字留底，避免口頭約定事後爭議。",
                "品八七曜五行相剋週，工作中可能遇到計畫外變動。保持彈性，準備好備案，把變化視為展現應變能力的機會。"
            ],
            # 中性：無直接生剋
            "neutral": [
                "七曜五行中性週，事業穩定推進。沒有特別的順風或阻力，靠自己的節奏穩步前進即可。",
                "七曜五行中性週，本週適合做工作上的長期規劃。趁環境平靜想清楚下個月甚至下一季的重點方向。"
            ]
        },
        "love": {
            "same": [
                "七曜五行同元素週互動自在，魅力值偏高。有伴的人適合安排約會，單身的人可以主動出擊。",
                "七曜五行同元素週，情感表達力本週好。平時不太會說的話，這週說出來反而很自然。想對重要的人說什麼，別再拖了。"
            ],
            "generating": [
                "品八七曜五行相生週，感情上被支持的感覺強。另一半比平時體貼，朋友也可能主動幫你牽線。",
                "品八七曜五行相生週，社交運佳，適合參加聚會或約會。本週散發的親和力讓人想靠近，是拓展新關係的好時機。"
            ],
            "weakening": [
                "品八七曜五行相洩週，可能因疲倦而顯得冷淡。跟另一半或朋友解釋一下你的狀態，別讓對方誤解。",
                "品八七曜五行相洩週，本週情緒波動較大，別在心情不好時做感情的重大決定。先調整好自己的狀態再說。"
            ],
            "conflicting": [
                "品八七曜五行相剋週，人際互動可能有些小摩擦。有誤會就當場說清楚，別讓小問題發酵。",
                "品八七曜五行相剋週，跟另一半的溝通本週需要多一點耐心。不用爭出勝負，互相理解比贏了辯論重要。"
            ],
            "neutral": [
                "七曜五行中性週感情平淡穩定。沒有浪漫驚喜也沒有煩心事，利用平靜好好陪伴在意的人。",
                "七曜五行中性週，社交節奏隨意調整。想約人就約，想獨處就獨處，順其自然的互動最舒服。"
            ]
        },
        "health": {
            "same": [
                "七曜五行同元素週身體狀態穩定。適合維持或加強運動習慣，體能和精神在正常範圍。別因感覺好就過度操勞。",
                "七曜五行同元素週，健康方面本週沒有特別問題。保持正常作息和飲食即可，多喝水、少喝含糖飲料。"
            ],
            "generating": [
                "品八七曜五行相生週精力充沛。適合增加運動強度或嘗試新運動。身體恢復力好，稍微累一點也能很快復原。",
                "品八七曜五行相生週，身體代謝效率本週偏高，是調整飲食或開始健康計畫的好時機。做出的改變比較容易看到效果。"
            ],
            "weakening": [
                "品八七曜五行相洩週容易感到疲累。晚上盡量在十一點前上床，減少咖啡因。肩頸很緊的話花十分鐘做伸展。",
                "品八七曜五行相洩週，免疫力本週可能稍微下降。注意保暖、避免太涼的食物。身體不舒服就休息，別硬撐。"
            ],
            "conflicting": [
                "品八七曜五行相剋週壓力可能反映在身體上。留意頭痛、肩頸僵硬、失眠等訊號。每天花十分鐘深呼吸或伸展。",
                "品八七曜五行相剋週，健康方面注意情緒對身體的影響。煩躁時用運動代替久坐，散步二十分鐘比滑手機兩小時有效。"
            ],
            "neutral": [
                "七曜五行中性週身體狀態平穩，維持現有健康習慣。有固定運動就繼續，還沒有就從每天走路三十分鐘開始。",
                "七曜五行中性週，本週健康管理以「維持」為主。保持穩定作息和飲食就是對身體最好的照顧。"
            ]
        }
    }

    # 月運主題描述（以 T21n1299 品二各日吉凶為基礎）
    # 描述本月整體氣氛，引用原典經文
    MONTHLY_THEME_DESCRIPTIONS = {
        # 栄「宜入官拜職、對見大人」親「宜結交、歡宴聚會並吉」(p.397c)
        "eishin": [
            "原典記載栄日「宜入官拜職、對見大人、上書表進獻君王、興營買賣」，親日「宜結交、定婚姻、歡宴聚會並吉」（T21 p.397c）。本月與本命宿形成栄親月，各項行動的成功率高於其他月份。把需要爭取、說服、推進的重要事項排在這個月。",
            "月宿與本命宿形成栄親的佳角度。品二所列的吉事——入官拜職、結交朋友、歡宴聚會——在這個月都有利。把最想做好的事排進來，成功率明顯高於其他時段。",
            "栄親月整體順暢。職場合作、人際拓展、業務推進都有利。原典多項「並吉」的記載，支持你在這個月積極行動。"
        ],
        # 業「所作善惡亦不成就、甚衰」胎「不宜舉動百事」(p.397c)
        "gyotai": [
            "原典記載業日「所作善惡亦不成就，甚衰」，胎日「不宜舉動百事」（T21 p.397c）。本月月宿與本命宿形成業胎關係，不管做什麼都不容易有結果。這不是你的問題，而是月運週期走到了低點。收斂觀望，把力氣留給更好的月份。",
            "業胎月的原典基調是「不成就」和「不宜舉動」。與其勉強推進，不如利用這段時間整理資訊、學習充電、規劃下一步。品三記載「宜修功德」（T21 p.391b），向內充實比對外行動更有價值。",
            "月宿與本命宿處於業胎位置（品二 T21 p.397c），外在行動的回報率低。接受這個月的節奏，安靜蓄力。等業胎月過去，新的栄親或友衰月到來時，你已經準備好了。"
        ],
        # 命「不宜舉動百事」(p.397c) + 「宜修功德」(品三 p.391b)
        "mei": [
            "原典記載命日「不宜舉動百事」（T21 p.397c），品三記載「宜修功德」（T21 p.391b）。本命宿回歸的月份，適合停下來看清楚自己的方向。職涯規劃、生活重心、人際取捨，趁這個月靜下來想清楚，比急著行動更有用。",
            "命月讓你暫時抽離日常忙碌，退一步看全局。花時間做復盤、整理資訊、重新規劃優先順序，這些看似不產出的行為，是在為下一波行動蓄力。原典所說的「修功德」就是這個意思。",
            "品二命日（T21 p.397c），本月適合做減法。占用時間但沒有回報的活動、半途而廢的計畫，趁命月的清醒做出取捨。留下來的才是真正重要的，之後精力更集中。"
        ],
        # 友「宜結交朋友大吉」衰「唯宜解除諸惡、療病」(p.397c-398a)
        "yusui": [
            "原典記載友日「宜結交朋友大吉」，衰日「唯宜解除諸惡、療病」「不宜出入遷移、買賣」（T21 p.397c-398a）。友衰月的能量平緩穩定，社交吉但不宜大動作。那些需要耐心、需要反覆練習的事，在這個月做最合適。",
            "友衰月節奏穩定（T21 p.397c-398a）。友日的人際互動順暢，衰日則適合處理拖延已久的問題。利用這份平穩做被拖延的事：整理環境、更新資料、清掉待辦清單。",
            "品二友衰（T21 p.397c-398a），不要跟別人比進度。友衰月你正好在蓄力，別人在衝刺的時候你穩穩累積，這完全正常。衰日「唯宜解除諸惡」（T21 p.398a），把問題一個個解決就是最好的推進。"
        ],
        # 危「宜結交、不宜遠行買賣」成「宜修道學問」(p.397c-398a)
        "kisei": [
            "原典記載危日「宜結交、歡宴聚會並吉」「不宜遠行出入移徙、買賣」，成日「宜修道學問、作諸成就法並吉」（T21 p.397c-398a）。危成月帶有半吉半忌的特質，做事可能遇到部分阻力。提前做好備案、重要文件多檢查一遍。",
            "危成月的策略是分場景應對。成日「宜修道學問」——學習、研究、精進的效率高；危日「不宜遠行買賣」（T21 p.397c-398a）——出差和大額交易需謹慎。分清宜忌，就能把風險控制在最小。",
            "品二危成（T21 p.397c-398a），人際互動上需要多一份耐心。危成月的張力容易讓溝通出現摩擦，遇到不舒服的時候先冷靜再回應，能省掉不少麻煩。"
        ],
        # 安「移徙吉、造作園宅」壊「餘並不堪」(p.397c-398a)
        "ankai": [
            "原典記載安日「移徙吉、遠行人入宅、造作園宅、作壇場並吉」，壊日「宜作鎮壓、降伏怨讎，餘並不堪」（T21 p.397c-398a）。安壊月的整體能量偏低，壊日「餘並不堪」限制了大部分行動。最好的應對是順勢而為：安頓環境的事放心做，其他減少。",
            "品二安壊（T21 p.397c-398a），安壊月不適合冒險和擴張。守住手上已有的成果，把做到一半的事情收尾，比開始新計畫更有價值。安日「移徙吉」（T21 p.397c），如果有整理環境、調整空間的需求，這個月倒是順手。",
            "壊日「餘並不堪」（T21 p.398a）是這個月的基調限制。別急著抓住每個機會，先觀察幾天確認沒問題再行動。多聽信任的人怎麼說，用別人的視角補充自己看不到的盲點。"
        ]
    }

    # 年運建議（基於 T21n1299 品八七曜五行 + 九曜寺院傳承）
    # 干支元素與本命元素的五行關係 → 年度行動建議
    YEARLY_FORTUNE_ADVICE = {
        # 同元素：干支與本命同屬一元素
        "same": [
            "今年干支與本命同屬一元素（品八七曜五行，T21 p.399a）。個人特質被放大，擅長的領域得心應手。建議深耕現有優勢，同時安排自我檢視，避免在舒適圈停滯。",
            "同元素年份（品八七曜五行，T21 p.399a）是鞏固根基的好時機。過去累積的技能和人脈在今年自然發酵，把基本功做紮實，讓專業能力經得起時間考驗。",
            "同元素共振（品八七曜五行，T21 p.399a）穩定但容易思維固化。把精力集中在最有優勢的領域，用深耕取代廣撒，主動接觸不同領域的人帶來新視野。"
        ],
        # 相生：干支元素生本命元素
        "generating": [
            "五行相生年份（品八七曜，T21 p.399a），外在環境在支持你。適合擴張的年份——換工作、拓展業務、嘗試新技能，成功率比平時高。注意品質管控不要鬆懈。",
            "五行相生年份（品八七曜，T21 p.399a），做事阻力變小，過去推不動的案子可能出現轉機。聚焦在兩三個最重要的目標上效果最好。",
            "品八七曜五行相生年份（T21 p.399a）是學習加速期。吸收力和理解力特別強，適合報名課程、考取證照、深入研究新領域。投資自己的回報率高。"
        ],
        # 相洩：本命元素生干支元素
        "weakening": [
            "今年本命元素滋養干支（品八七曜五行相洩，T21 p.399a），付出會比較多。學會管理能量，定期休息充電。每個月留幾天完全放空，不要燃燒殆盡。",
            "品八七曜五行相洩年份（T21 p.399a），做同樣的事需要比以前多花力氣。效率比努力重要——學會說不、設定界線，少做但做好。",
            "品八七曜五行相洩（T21 p.399a），今年的關鍵字是「精簡」。能量有限，列出最想完成的三件事，其他放到候補。飲食均衡和充足睡眠是今年的底線。"
        ],
        # 相剋：干支元素剋本命元素
        "conflicting": [
            "今年干支元素與本命形成五行相剋（品八七曜，T21 p.399a），外在環境帶有張力。面對困難善用團隊和外部資源，學習借力使力。急躁是今年最大的敵人。",
            "品八七曜五行相剋年份（T21 p.399a）需要不同策略。直線受阻時換角度繞路反而更快。培養耐性和彈性，穩住節奏化險為夷。",
            "品八七曜五行相剋（T21 p.399a），張力年份的摩擦是在磨掉不需要的稜角。控制情緒，不要在壓力下做重大決定，等風頭過了再定奪。"
        ],
        # 九曜凶年（宿曜道寺院傳承：放生寺/大聖院/岡寺）
        "kyo": [
            "九曜循環走到凶星年（宿曜道寺院傳承）。九年一次的低潮，最務實的策略是縮小戰線：「必須做」和「可以等」分清楚，只留必須的。不要啟動新計畫、跳槽、或大量投入資源。守住現有的，遇到重大決定先擱七天。",
            "九曜凶星年（寺院傳承：放生寺/大聖院）。辛苦但不等於毀滅，低谷之後就是回升。安全度過是首要目標：減少社交應酬、推掉高風險邀約、避免借貸和大額投資。話到嘴邊停三秒再說。",
            "九曜凶星年（宿曜道寺院傳承）。低潮年的好處：幫你看清什麼才是真正重要的。今年不追求成長，追求穩定。把生活作息固定、把身體照顧好、把核心關係維護住。"
        ],
        # 中性：無直接生剋
        "neutral": [
            "今年干支元素與本命無明顯衝突或加持（品八七曜五行中性，T21 p.399a），自主空間最大。你的主動作為決定年度成績，自律的人在這種年份最容易拉開差距。",
            "品八七曜五行中性年份（T21 p.399a）適合制定長期計畫並穩定推進。外在變數少，可以專心把手上的事做到最好。",
            "品八七曜五行中性（T21 p.399a），沒有明顯的順風或逆風。適合需要長時間持續投入的事——學語言、養成運動習慣、系統性整理財務。日拱一卒。"
        ]
    }

    # 年度主題敘事（基於 T21n1299 品八七曜五行 + 九曜寺院傳承）
    # 干支元素與本命元素的五行關係 → 年度整體走向
    YEARLY_THEME_DESCRIPTIONS = {
        # 同元素：干支與本命同屬一元素，能量共振
        "same": [
            "今年干支與本命同屬一元素（品八七曜五行，T21 p.399a）。同元素共振放大你的核心特質，擅長的領域表現突出，直覺更準、決策更果斷。但同頻也意味著盲點會被放大。找信任的朋友定期交換想法，用外部視角修正死角。適合深耕，把已有基礎的技能或關係往上推一個層次。",
            "同元素年份（品八七曜五行，T21 p.399a）像一面放大鏡。你最自豪的能力更突出，短板也無處躲藏。年初花一個月做自我盤點，列出三項要強化的優勢和兩項要正視的不足，然後用剩下的十一個月紮實推進。穩定輸出的一年，結果取決於你的紀律。",
            "今年干支與本命同屬一元素（品八七曜五行，T21 p.399a），外在環境映射你的內在能量。你擅長什麼，機會就往哪邊靠攏。過去累積的人脈、技能、聲譽會自然轉化為實際報酬。做你最擅長的事，穩住節奏。"
        ],
        # 相生：干支元素生本命元素，外在滋養
        "generating": [
            "五行相生年份（品八七曜，T21 p.399a），外在能量支持你，申請的東西更容易通過、合作提案更容易被接受、學新技能的速度也快了。把一直想做但沒開始的事排進今年計畫。順利的時候定期停下來檢查方向是否正確。",
            "五行相生年份（品八七曜，T21 p.399a）的優勢是「吸引力」——你的狀態好的時候，別人更願意跟你合作。充分利用這個優勢建立長期關係，今年種下的種子會在未來兩三年持續結果。集中在兩三個核心目標上效果最好。",
            "五行相生（品八七曜，T21 p.399a），今年學習能力和適應力都在高峰。轉換跑道、學新技術、進入陌生社交圈，上手速度比預期快。年初勇敢跨出舒適圈，年底回頭看會慶幸沒猶豫。上半年啟動新嘗試，下半年鞏固深化。"
        ],
        # 相洩：本命元素生干支元素，能量外流
        "weakening": [
            "今年本命元素滋養干支（品八七曜五行相洩，T21 p.399a），能量向外流出較多。付出大於回收是這年的特徵。能量管理是最重要的課題：把時間和精力視為有限預算來分配，每週留至少一天完全放空。做得少但做得好，比什麼都沾一點但全部六十分好得多。",
            "五行相洩年份（品八七曜，T21 p.399a）需要換打法。正確的策略是「精準投入」——砍掉沒實質幫助的社交、推掉沒回報的額外工作，把時間留給真正重要的少數事。在幫助別人的過程中你反而會學到東西。",
            "品八七曜五行相洩（T21 p.399a），今年最需要的是「設界」——設定界線。不主動控制輸出量，年底會覺得被掏空。學會說「這個我做不了」。健康是今年的底線，飲食、睡眠和運動是必答題。"
        ],
        # 相剋：干支元素剋本命元素，外在張力
        "conflicting": [
            "今年干支元素與本命形成五行相剋（品八七曜，T21 p.399a），能量場帶有摩擦和張力。計畫可能被打斷、人際互動出現衝突。退一步想清楚再行動比硬撐有效。今年培養的耐性和應變力會成為未來幾年最重要的資產。避免在壓力大時做重大決定。",
            "五行相剋（品八七曜，T21 p.399a）帶來的張力也是轉化契機。你會被迫面對一直在逃避的問題，過程不舒服但解決後你會脫一層皮。保持彈性、控制情緒、遇到卡關就換個方式試。",
            "品八七曜五行相剋（T21 p.399a），今年的策略是「繞路前進」。直線走不通時換個角度切入反而更快。放下對既定方案的執著，用變通取代固執。和某些人的關係可能緊張，不是誰對誰錯，而是頻率暫時不同步，給彼此空間。"
        ],
        # 九曜凶年（宿曜道寺院傳承：放生寺/大聖院/岡寺）
        "kyo": [
            "今年是九曜循環中的凶星年（宿曜道寺院傳承）。外在環境支持力降到最低，做什麼都比平時費勁。最聰明的做法是承認現實然後調整打法：把目標從「往前衝」改成「不後退」。守住工作、守住健康、守住重要的人。九曜循環不會停在這裡，低谷的另一邊就是回升。",
            "九曜凶星年（寺院傳承：放生寺/大聖院）。事情的發展可能不會照你的劇本走，你現在的任務不是逆轉局面而是保存實力。把精力集中在三件事——睡好、吃好、和讓你安心的人保持聯繫。大決定能拖就拖，等狀態回來再做。",
            "九曜凶星年（宿曜道寺院傳承）。低谷年的特徵是「什麼都慢半拍」。趁這段強制減速的時間做平常沒空做的事：整理文件、聯繫老朋友、想想接下來三年你到底想過什麼樣的日子。這一年不會給你舞台，但會給你思考的空間。"
        ],
        # 中性：無直接生剋
        "neutral": [
            "今年干支元素與本命無明顯衝突或加持（品八七曜五行中性，T21 p.399a）。你有最大的自主權來決定這一年要過成什麼樣子。你做什麼就得什麼，付出多少就回收多少。年初花兩週認真規劃全年，用季度為單位檢核進度。最終結果完全是你行動的總和。",
            "品八七曜五行中性年份（T21 p.399a）像一張白紙。環境退到背景裡，把舞台完全留給你。適合做需要長期穩定投入的事情：學語言、寫作、建立被動收入、經營深度關係。沒有外力干擾的時期最適合專注。",
            "品八七曜五行中性（T21 p.399a），今年的節奏是「日拱一卒」。不需要大爆發、不需要抓住轉瞬即逝的機會。每天做好手邊的事，每月檢視一次方向。穩定的一年，成果取決於持續性而非爆發力。"
        ]
    }

    # 年度各項分述（基於 T21n1299 品八七曜五行 + 九曜寺院傳承）
    # 干支元素與本命元素的五行關係 → 事業/感情/健康/財運分述
    # kyo = 九曜凶星年（宿曜道寺院傳承：放生寺/大聖院/岡寺）
    YEARLY_CATEGORY_DESCRIPTIONS = {
        "career": {
            "same": [
                "事業方面，七曜五行同元素共振（T21 p.399a），你的專業能力被放大。在自己的領域裡如魚得水，同事和主管會更加信任你的判斷。適合深耕現有職位、爭取更大的責任範圍。但要注意不要因為太熟練而失去創新的動力。",
                "七曜五行同元素共振（T21 p.399a），今年的職場表現穩定而扎實。你的工作風格和環境需求完全匹配，推進專案的效率比往年高。如果有升遷機會，主動爭取的成功率不低。別在舒適圈裡待太久，偶爾接一些有挑戰的任務來維持成長。"
            ],
            "generating": [
                "七曜五行相生（T21 p.399a），事業運勢旺盛，外部環境在推你向上。今年很適合換工作、創業、或者在公司內部爭取新的職位。你提出的想法比較容易被採納，跨部門合作也比較順利。年初就鎖定目標，用上半年衝刺，下半年穩固成果。",
                "七曜五行相生（T21 p.399a），今年職場上的貴人特別多。有人會主動拉你一把、介紹你認識關鍵人物、或者給你一個意想不到的機會。保持開放心態，別急著說不。同時提升自己的可見度——不是張揚，而是讓你的專業成果被需要看到的人看到。"
            ],
            "weakening": [
                "品八七曜五行相洩（T21 p.399a），事業上今年需要多花一些力氣。你可能被分配到更多的工作量，或者需要處理別人留下的爛攤子。這不是你能力不夠，而是能量消耗型年份的正常現象。把精力集中在最能展現價值的兩三件事上，其他的用最低限度的標準過關即可。",
                "品八七曜五行相洩（T21 p.399a），今年職場上的主旋律是「守成」。不是擴張的好時機，但很適合把手上的事情做到極致。把流程優化、把關係經營好、把基礎打牢。等能量恢復的年份到來時，你現在的積累會成為衝刺的資本。"
            ],
            "conflicting": [
                "品八七曜五行相剋（T21 p.399a），事業上今年會遇到一些意外的挑戰。計畫被打亂、合作對象臨時變卦、市場風向突然轉彎。這些變數不一定是壞事，因為有些更好的機會藏在變化裡。保持彈性，不要死抱著原來的計畫不放。讓自己有空間嘗試計畫B和C。",
                "品八七曜五行相剋（T21 p.399a），職場人際需要額外經營。你和同事或主管之間可能出現理解上的落差，多確認、多溝通能避免大部分問題。不要用情緒去處理工作上的衝突，冷靜幾天再回應，結果往往比當下反應好得多。"
            ],
            "kyo": [
                "九曜凶星年（宿曜道寺院傳承），今年的職場不適合主動出擊。不要在這一年跳槽、要求大幅加薪、或者跟主管正面衝突。先穩住現有位置，把手上的工作做到不出錯就好。如果被裁員或被迫轉換，不要急著做決定，給自己至少兩週的冷靜期再行動。低潮年做的職涯決定很容易後悔。",
                "九曜凶星年（宿曜道寺院傳承），工作上遇到不公平的事情，今年不是正面交鋒的時機，但可以把它當成觀察和學習的素材。記錄下來，想清楚你真正在意的是什麼、你希望怎麼被對待。同時，趁這段時間補強自己的技能、整理作品集、維護關鍵人脈。低谷年做的準備工作，會在下一波機會來臨時直接變現。"
            ],
            "neutral": [
                "干支五行中性（品八七曜，T21 p.399a），事業表現取決於你自己的投入程度。今年不會有天上掉下來的好機會，但也不會有無法預見的絆腳石。制定清晰的季度目標，踏實推進即可。最適合用來累積技能、建立長期競爭力、深化專業領域的知識。",
                "干支五行中性，今年的職場環境穩定，沒有太多外力干擾。利用這段平靜期做一些需要專注的事情：考證照、寫專業文章、整理作品集。這些短期看不到回報的投入，會在未來的某個時刻突然派上用場。"
            ]
        },
        "love": {
            "same": [
                "感情方面，七曜五行同元素共振（T21 p.399a），同頻年份讓你對自己想要什麼更清楚。不管是單身還是有伴，你都會更誠實地面對內心需求。單身者今年容易遇到價值觀相近的人，不用急著找，但要讓自己出現在對的場合。有伴侶的人關係穩定中帶著一點舒適感，安排一些共同的新體驗來增添火花。",
                "七曜五行同元素共振（T21 p.399a），感情裡的你今年特別有魅力，同元素加持讓你更自信、更從容。這種由內而外的吸引力是最持久的。單身者如果遇到喜歡的人，主動出擊的成功率高。有伴的人雙方默契增加，適合討論一些關於未來的規劃。"
            ],
            "generating": [
                "七曜五行相生（T21 p.399a），感情運勢很好，桃花旺但不亂。今年遇到的人品質比較高，能讓你有「終於遇到對的人」的感覺。不過別因為太順利就省略了解對方的過程，好的感情需要時間來確認。有伴的人適合規劃婚事或者一起完成一件有意義的事。",
                "七曜五行相生（T21 p.399a），今年在感情中你會感覺被支持和理解。另一半比平時更願意配合你，朋友也會主動幫你介紹對象。善用這股好運，但也要記得付出。感情是雙向的，你接收到的善意需要以另一種形式回饋。"
            ],
            "weakening": [
                "品八七曜五行相洩（T21 p.399a），感情上今年需要多花心思經營。你可能因為工作忙碌而忽略了另一半，或者因為精力有限而對社交失去興趣。但感情不是你忙就能暫停的東西，每週至少留出一段不被打擾的時間給重要的人。單身者不用急著找對象，先把自己的狀態調整好再說。",
                "品八七曜五行相洩（T21 p.399a），有伴的人今年要注意溝通品質。你可能因為累而說話比較直接，對方不一定能理解你只是疲倦而不是不在乎。有話好好說，用文字表達不了的東西就當面談。關係裡偶爾示弱不是認輸，是讓對方知道你需要他。"
            ],
            "conflicting": [
                "品八七曜五行相剋（T21 p.399a），感情方面今年有些波折。可能遇到價值觀衝突、生活節奏不合拍、或者對未來的期待不同。這些問題藏在水面下很久了，今年它們浮上來反而是好事。正面處理比假裝沒看到好。不管結果如何，誠實面對是唯一的出路。",
                "品八七曜五行相剋（T21 p.399a），單身的人今年的桃花帶有一點試煉的意味。你遇到的人可能讓你心動但又讓你猶豫，那種矛盾感其實是在幫你釐清你真正需要的是什麼類型。不急著確定關係，多觀察、多了解，等張力過去之後再做決定。"
            ],
            "kyo": [
                "九曜凶星年（宿曜道寺院傳承），感情上今年最好的策略是「不折騰」。盡量不要在這一年做感情裡的重大決定——低潮期的情緒容易影響你看待關係的方式，等心境穩定之後再回頭評估會更客觀。有伴的人就好好相處，吵架的時候先離開現場，冷靜之後再談。單身的人不用急，把注意力放在照顧自己上面，狀態好了自然會吸引對的人。",
                "九曜凶星年（宿曜道寺院傳承），今年感情裡最需要的是一個讓你安心的存在。不一定是戀人，可以是家人、摯友、任何讓你在身邊就覺得世界沒那麼糟的人。主動跟這些人保持聯繫，累的時候打個電話、週末約出來吃頓飯。不要自己扛，也不要覺得麻煩別人丟臉。有伴的人今年把另一半當隊友而不是觀眾，一起面對比各自承擔有效得多。"
            ],
            "neutral": [
                "干支五行中性（品八七曜，T21 p.399a），感情上今年不溫不火，適合穩定經營。不會有戲劇化的轉折，但會有日常相處裡的小確幸。有伴的人適合把注意力放回基本功——好好吃飯、好好聊天、好好休息。單身者不用焦慮，但也別把自己封閉起來，保持正常的社交頻率即可。",
                "干支五行中性，今年感情的主題是「品質大於數量」。深度的交流比頻繁的約會有價值，了解一個人的內在比外在條件更重要。如果你想要一段長久的關係，今年的穩定環境非常適合慢慢培養。"
            ]
        },
        "health": {
            "same": [
                "健康方面，七曜五行同元素共振（T21 p.399a），身體狀況基本穩定。你的體質和今年的能量頻率合拍，不容易出大問題。但「穩定」不等於「不用管」，正因為今年沒什麼警訊，很容易忽略那些緩慢累積的隱患。維持規律的運動、均衡的飲食，安排一次全面的健康檢查。預防永遠比治療便宜。",
                "七曜五行同元素共振（T21 p.399a），今年身體底子好，適合建立長期的健康習慣。不管是開始跑步、學游泳、還是調整飲食結構，今年養成的好習慣比較容易堅持下去。不要等到身體發出警告才行動，趁狀態好的時候投資健康。"
            ],
            "generating": [
                "七曜五行相生（T21 p.399a），健康運佳，今年是改善體質的好時機。如果你想減重、增肌、或者改善某個長期的小毛病，今年的效果會比較明顯。身體的恢復力也比較好，即使偶爾熬夜或作息不正常，也能比較快恢復。但別因此就糟蹋自己。",
                "七曜五行相生（T21 p.399a），今年的精力充沛，做什麼都不太容易累。但這股好狀態需要用正確的方式運用——規律運動把多餘的能量消耗掉，而不是用加班來填滿。適合嘗試一項新的運動，或者把運動頻率從一週三次提高到四五次。"
            ],
            "weakening": [
                "品八七曜五行相洩（T21 p.399a），健康是今年最需要關注的項目。能量外流讓你比平時更容易疲勞，免疫力可能也稍微下降。感冒、過敏、腸胃不適這些小問題可能比往年頻繁。強烈建議每天保證七到八小時的睡眠，減少咖啡因和酒精的攝取。不要硬撐，身體的信號比你的意志力準確得多。",
                "品八七曜五行相洩（T21 p.399a），今年你的身體在提醒你欠的債。過去幾年高強度運轉累積的疲勞可能在今年集中爆發。不要害怕，這是身體在自我修復。配合身體的需求，該休息就休息、該看醫生就看醫生。養好今年，未來才有本錢衝刺。"
            ],
            "conflicting": [
                "品八七曜五行相剋（T21 p.399a），健康上今年要多留心壓力對身體的影響。張力年份帶來的焦慮可能導致失眠、頭痛、肌肉緊繃、或者消化不良。找到適合你的紓壓方式是今年的必修課——不管是運動、冥想、還是單純找人聊天。不要讓壓力在體內累積到爆炸才處理。",
                "品八七曜五行相剋（T21 p.399a），今年容易因為趕時間而忽略身體警訊。養成每天用五分鐘掃描身體狀態的習慣：哪裡痠、哪裡緊、睡得夠不夠、吃得好不好。小問題及時處理，就不會演變成大問題。安排上半年做一次健檢，及早發現及早處理。"
            ],
            "kyo": [
                "九曜凶星年（宿曜道寺院傳承），健康是今年需要比平時更主動關注的項目。低潮年的身體恢復速度會比較慢，所以預防比治療更重要。每天睡滿七小時、三餐正常吃、每週至少走路三十分鐘——這些基本功就是你最好的護身符。如果出現不舒服的症狀，早點去看醫生，不要拖。今年安排一次完整健檢，有問題及早處理，沒問題就安心。把身體照顧好，其他事情才有底氣去面對。",
                "九曜凶星年（宿曜道寺院傳承），今年的壓力會直接反映在身體上。失眠、偏頭痛、腸胃不適、莫名的疲倦感，這些都是身體在幫你喊停。不要硬撐，累了就休息、扛不住就求助。減少咖啡因和酒精的攝取，它們短期提神但長期消耗你的修復能力。找到一個能讓你放鬆的固定儀式：泡澡、散步、聽音樂、什麼都好，每天給自己半小時完全不用想事情的時間。身體撐住了，其他的才有談的餘地。"
            ],
            "neutral": [
                "干支五行中性（品八七曜，T21 p.399a），健康狀態平穩，今年適合做體質管理。沒有特別需要擔心的大問題，但也不要因此就放縱生活作息。把健康管理視為一種長期投資，今年投入的每一分努力都會在未來幾年得到回報。建立固定的運動時間、改善飲食結構、保持充足的睡眠。",
                "干支五行中性，今年的身體不會給你太多警告，所以你需要主動去關心它。定期量體重、記錄睡眠品質、觀察皮膚和精神狀態的變化。這些日常的微調比一年做一次健檢更能即時反映你的健康狀況。"
            ]
        },
        "wealth": {
            "same": [
                "財運方面，七曜五行同元素共振（T21 p.399a），你對金錢的感知力更強。你能比平時更精準地判斷哪些錢該花、哪些錢該存、哪些投資值得跟。適合重新審視你的財務結構——保險夠不夠、緊急預備金有沒有三到六個月的生活費、投資組合是否需要調整。用你今年特別敏銳的財務直覺，做一些長期有利的理財決策。",
                "七曜五行同元素共振（T21 p.399a），今年的財務狀態穩定，沒有太大的起伏。收入和支出都在預期範圍內，不會有突如其來的大額開支或意外之財。這種穩定期最適合打好理財基礎：清掉小額負債、建立自動存款機制、學一點基礎的投資知識。"
            ],
            "generating": [
                "七曜五行相生（T21 p.399a），財運旺盛，今年有不錯的增加收入的機會。可能是加薪、獎金、副業收入、或者投資回報。但「有機會」不等於「自動到手」，你需要主動爭取——該談薪資就談、該爭取專案獎金就爭取。同時控制花費，別因為賺得多就花得多，把多出來的收入存下來或者投入增值資產。",
                "七曜五行相生（T21 p.399a），今年的錢會從意想不到的管道流進來。保持開放心態，不要拒絕看起來不太傳統的賺錢機會。當然，天上不會掉餡餅，如果一個機會好到不真實，花時間確認清楚再行動。正當管道的機會今年確實比較多。"
            ],
            "weakening": [
                "品八七曜五行相洩（T21 p.399a），財務方面今年要做好「花多存少」的心理準備。不是你會虧錢，而是你需要花錢的地方比預期多——可能是維修費、醫療費、人情費、或者不得不做的升級投資。提前留出一筆預備金，遇到必要開支時才不會手忙腳亂。能省的地方省，不能省的地方不要省。",
                "品八七曜五行相洩（T21 p.399a），今年不適合做高風險的投資或大額的衝動消費。把注意力放在「不虧」上面，穩穩地守住已有的資產比追求高報酬更重要。如果必須做財務決策，找專業的人諮詢，不要靠感覺。"
            ],
            "conflicting": [
                "品八七曜五行相剋（T21 p.399a），財務上可能有一些意外的波動。你以為穩賺的投資可能出現回檔、預期的收入可能延遲入帳、突然冒出一筆計畫外的開支。應對的方式是：不要把所有雞蛋放在一個籃子裡，保持財務的靈活性。手邊永遠留一筆三到六個月的生活費，讓自己有餘裕應對變化。",
                "品八七曜五行相剋（T21 p.399a），今年在花錢之前多想三秒。衝動消費和衝動投資是張力年份最容易犯的錯。看到好東西先放進購物車等兩天、聽到好機會先記下來研究一週。過了冷靜期還覺得值得的，再花錢也不遲。"
            ],
            "kyo": [
                "九曜凶星年（宿曜道寺院傳承），財務上今年的核心策略是「穩健」。盡量不借錢、不做沒有把握的投資、遇到重大財務決定先多方確認再行動。低潮年的環境干擾比較多，容易讓人做出衝動的金錢決定，多給自己一點思考時間不會吃虧。手邊的現金留越多越好，至少準備六個月的生活費當安全墊。如果已經有投資部位，不要加碼也不要恐慌賣出，維持現狀就好。今年的目標不是賺錢，是穩穩守住。",
                "九曜凶星年（宿曜道寺院傳承），今年可能會遇到一些意料之外的開支：車子壞了、家電要換、身體需要治療、朋友開口借錢。提前把預備金準備好，遇到的時候才不慌。能不花的錢就不花，能晚付的帳就晚付。如果有人跟你推銷保險、基金、或任何理財商品，一律說「我再想想」然後放到明年再決定。低谷年守住荷包比什麼都重要。"
            ],
            "neutral": [
                "干支五行中性（品八七曜，T21 p.399a），財務狀態平穩，沒有大起大落。這種環境最適合做長期理財規劃——定期定額投資、重新配置資產比例、或者開始研究一個你一直想了解的投資工具。不要期待今年有爆發性的財務增長，但持續穩定的累積到年底也是一筆可觀的數目。",
                "干支五行中性，今年的財運中規中矩，收入跟付出成正比。想多賺就得多做，沒有捷徑。把注意力放在提升自己的賺錢能力上面——技能升級帶來的加薪、作品集帶來的副業機會——這些投入的回報比任何理財技巧都可靠。"
            ]
        }
    }

    # 角色別相處建議（基於 T21n1299 品二六關係延伸，編者歸納）
    # 品二記載六關係（栄親/友衰/危成/安壊/命/業胎）的吉凶性質
    # 此處將六關係特質延伸至不同身份的互動情境
    ROLE_DESCRIPTIONS = {
        # 栄親：品二「宜入官拜職、對見大人」「宜結交、歡宴聚會並吉」（T21 p.397c）
        "eishin": {
            "colleague": "栄親在職場上是最強的搭檔組合。你們天然地互相加持，一個人的提案被另一個人補充之後總是變得更完整。分工的時候各自負責擅長的部分，彙整時反而比一個人全做更快更好。如果有機會合作專案，不要猶豫直接組隊。唯一要注意的是功勞的歸屬——因為你們太容易合作成功，有時候會忘了釐清各自的貢獻，事先講清楚比事後爭論好。",
            "friend": "栄親的友誼有一種自然而然的滋養感，跟對方聊完天之後你會覺得被充電了。你們適合一起做有建設性的事——一起運動、一起學東西、一起參加活動。這種朋友不會讓你越來越懶，反而是在對方身邊你會不自覺地想變得更好。遇到人生重大決定的時候，聽聽對方的想法，栄親朋友給的建議通常特別有參考價值。",
            "lover": "栄親在感情中是越相處越舒服的類型。初識時可能不是一見鍾情的驚天動地，但日子一長你會發現這個人讓你的生活全面升級。彼此的價值觀契合度高，生活習慣也容易磨合。重點是兩個人都要有各自的舞台——如果只有一方在成長，另一方容易產生不安全感。安排定期的共同活動和各自的獨處時間，維持健康的距離。",
            "family": "栄親關係的家人相處起來最輕鬆。你們之間的理解是天然的，很多事不需要解釋對方就能體會。作為親子關係，父母和孩子之間很少有真正的衝突，因為雙方都願意替對方著想。作為兄弟姐妹，你們是對方最強的後盾。家庭中如果有重大決策需要討論，你們之間的溝通效率最高。"
        },
        # 業胎：品二「所作善惡亦不成就，甚衰」「不宜舉動百事」（T21 p.397c）
        "gyotai": {
            "colleague": "業胎關係的同事之間有一種說不出的默契，有時候對方還沒開口你就知道他想表達什麼。合作的時候可以省掉很多溝通成本，工作節奏也容易對上。不過要注意一點：你們太熟悉彼此的思考模式，有可能陷入同溫層效應。遇到需要創新的時候，主動引入第三方的觀點來打破慣性思維。",
            "friend": "業胎的朋友像是認識了很多年的老友，即使很久沒聯絡，見面之後馬上回到上次離開的地方。你們之間不需要客套，可以直接說真話而不擔心傷感情。這種朋友不多，珍惜這份默契。但也因為太舒服了，有時候會忽略主動關心對方的近況，定期聯繫不要讓距離把默契消磨掉。",
            "lover": "業胎在感情中有一種宿命般的吸引力，認識的時候常有「這個人我好像在哪裡見過」的感覺。交往之後會發現很多價值觀、生活習慣甚至小癖好都相似。這種相似讓你們相處起來極度自在，但長期來說需要刻意製造一些新鮮感。一起嘗試新的興趣、去沒去過的地方旅行、突破日常的模式，讓這段關係保持活力。",
            "family": "業胎關係的家人之間有種深層的連結感，家庭聚會的時候你會發現跟這位家人特別聊得來。即使生活方式不同，你們對事情的看法往往出奇一致。如果需要一個能真正理解你的家人傾訴心事，這位業胎家人是首選。他們的建議通常最切合你的實際狀況，因為他們本能地懂你在想什麼。"
        },
        # 命：品二「不宜舉動百事」（T21 p.397c），品三「宜修功德」（p.391b）
        "mei": {
            "colleague": "命宿關係的同事就像照鏡子，你們的工作風格和思維方式極為相似。這有好有壞——好處是溝通零障礙，壞處是盲點也一模一樣。合作的時候要特別注意互相提醒對方看不到的地方，不要以為對方想到了就等於自己也不用擔心。分工的時候盡量負責不同的環節，避免重複勞動。",
            "friend": "命宿的朋友是最了解你的人，因為他們本質上跟你是同一類人。這意味著你最好的時候他們看得到，你最差的時候他們也瞞不過。這種友誼需要高度的自我接納——能接受對方身上那些跟自己一樣的缺點，才能真正享受這段關係。你們適合互相當對方的鏡子，坦誠地交換對彼此的觀察。",
            "lover": "命宿之間的感情帶有強烈的「終於被完全理解」的感受，對方的一個眼神你就知道他的情緒。但這份理解有時候是把雙面刃——因為太了解對方，吵架的時候也知道怎麼說最傷人。感情經營的重點是學會在衝突中控制情緒，不要利用對對方的了解來攻擊。你們需要約定好底線，有些話知道也不能說出口。",
            "family": "命宿的家人之間像是同一個模子刻出來的，性格、脾氣、甚至生活習慣都驚人地相似。相處起來很自在但也容易針鋒相對，因為對方身上你最看不慣的特質其實就是你自己的翻版。學會在這面鏡子前保持幽默感，笑著承認「你看，我們果然一樣」比互相指責有效得多。"
        },
        # 友衰：友「宜結交朋友大吉」衰「唯宜解除諸惡、療病」（T21 p.397c-398a）
        "yusui": {
            "colleague": "友衰在工作上需要注意能量的流向。友方在合作中通常主導節奏，衰方則容易被帶著走。如果你是友方，記得適時詢問對方的意見而不是一個人做決定。如果你是衰方，該表達的立場不要忍著不說。兩個人的能力其實差不多，只是互動模式容易形成固定角色，刻意打破這個慣性會讓合作更均衡。",
            "friend": "友衰的友誼通常很舒服，在一起時間過得特別快。但長期下來要注意是不是總在做一樣的事——一起吃飯、一起追劇、一起抱怨卻都不行動。好朋友應該互相推一把，偶爾提議做點新的事情，或者約對方一起報名課程。讓這段友誼不只是安慰劑，也是成長的觸媒。",
            "lover": "友衰的感情初期非常甜蜜，因為相處的舒適度很高。但進入穩定期之後，如果兩個人都不主動製造變化，容易陷入「哪裡都好但好像少了點什麼」的狀態。解方是設定共同目標：一起存錢旅行、一起健身、一起學新技能。有目標在前面拉著，你們會走得更有方向感。",
            "family": "友衰關係的家人相處融洽但容易形成依賴。如果你是友方的角色，家中的決定很多會由你主導，但記得這不代表衰方沒有想法，而是他們習慣讓你先說。主動問對方的意見，讓每個家人都有表達的空間。家庭中的能量越均衡，所有人的狀態都會越好。"
        },
        # 安壊：安「移徙吉、造作園宅」壊「宜鎮壓降伏、餘不堪」（T21 p.397c-398a）
        "ankai": {
            "colleague": "安壊在職場上的互動帶有競爭性的張力。壊方可能不自覺地表現得比較強勢，安方則會感受到壓力。如果能把這種張力引導到正面的競爭上，反而能激發出雙方最好的表現。關鍵是保持專業距離，把注意力放在工作成果上。私下建立信任也很重要——找機會在輕鬆的場合增加了解，減少不必要的防備心。",
            "friend": "安壊的友誼刺激但消耗能量。你們在一起的時候不無聊，但結束之後其中一方可能會覺得累。維持這段友誼的方法是控制強度和頻率——不需要天天見面，每隔一段時間聚一次反而每次都很精彩。也要留意權力動態有沒有失衡，健康的友誼不應該讓任何一方長期覺得委屈。",
            "lover": "安壊的愛情充滿激情和戲劇性。壊方的強勢在戀愛初期會讓安方覺得很有安全感，但時間一長如果壊方不學會收斂，安方會累積不滿。雙方必須在感情中建立對等的溝通機制：定期討論彼此的感受、設定不可逾越的底線、在衝突時給對方冷靜的空間。這段感情的天花板很高，但維護成本也不低。",
            "family": "安壊的家庭關係最需要有意識地管理。壊方在家中往往比較有主導權，安方容易委曲求全。如果是親子關係，壊方的家長要特別注意不要過度控制，安方的孩子需要更多被肯定和被聽到。營造一個每個人都能安全表達的家庭氛圍，比什麼都重要。衝突不可避免，但衝突後的修復才是維繫關係的關鍵。"
        },
        # 危成：危「宜結交、不宜遠行買賣」成「宜修道學問、成就法」（T21 p.397c-398a）
        "kisei": {
            "colleague": "危成在工作上是互補型的組合。成方負責規劃和執行，危方負責創意和突破。初期你們可能對彼此的工作方式感到困惑：「為什麼他要這樣做？」但磨合之後會發現這種差異其實是最大的資產。給彼此足夠的空間用各自的方式做事，在結果上對齊就好。過程中的差異不是問題，是互補。",
            "friend": "危成的友誼需要時間發酵。一開始你們可能覺得聊不到一起去，但某次深入的對話之後你會突然理解對方的世界觀——原來他看事情的角度跟你完全不同，卻同樣有道理。這種朋友的價值在於拓寬你的視野，跟你不一樣的觀點才能讓你看到盲點。比起聊天，一起做事更能加深你們的情誼。",
            "lover": "危成的感情前期需要比較多耐心，因為你們的生活節奏、溝通方式甚至審美偏好都不太一樣。但熬過磨合期之後，你們會成為非常穩固的伴侶。關鍵是接受對方跟你不同不代表他是錯的。學會欣賞差異而不是試圖改變對方，你們的感情會越磨越亮。定期安排約會夜，回到初識時那種好奇地探索對方的狀態。",
            "family": "危成的家庭關係需要雙方多練習理解力。你們看待事情的方式不同，容易因為觀念差異產生摩擦。但這種差異也讓家庭的視角更全面——做重大決定的時候，聽完所有人的意見通常能得到最平衡的結論。家庭聚會中不要急著否定對方的看法，先聽完再表達自己的想法，溝通品質會提升很多。"
        }
    }

    def _shift_level(self, level: str, direction: int) -> str:
        """
        等級位移

        Args:
            level: 當前等級 key (daikichi/kichi/chukichi/shokyo/kyo)
            direction: +1 = 提升一級, -1 = 降低一級

        Returns:
            位移後的等級 key（到頂/到底不再移）
        """
        idx = self.FORTUNE_LEVELS.index(level)
        # FORTUNE_LEVELS index 0 = 最佳(daikichi), 4 = 最差(kyo)
        # direction +1 表示提升（往 index 小的方向）
        new_idx = max(0, min(len(self.FORTUNE_LEVELS) - 1, idx - direction))
        return self.FORTUNE_LEVELS[new_idx]

    def _determine_daily_level(
        self, relation_type: str, ryouhan: Optional[dict],
        special_day_type: Optional[str]
    ) -> tuple[str, str, int]:
        """
        核心等級判定流程（原典邏輯）

        1. 本命宿 x 當日宿 → RELATION_LEVEL_MAP → base_level
        2. 凌犯判定 → RYOUHAN_LEVEL_FLIP
        3. 特殊日 → _shift_level(±1)
        4. 六害宿 → 不影響等級（warning only）

        Args:
            relation_type: 宿曜關係 (eishin/yusui/ankai/...)
            ryouhan: 凌犯資料（None = 不在凌犯期間）
            special_day_type: 特殊日類型 (kanro/rasetsu/kongou/None)

        Returns:
            (final_level, base_level, overflow_bonus) — 最終等級、原始等級、
            溢出加分（等級已在極值但特殊日仍有加持時的額外分數）
        """
        # Step 1: 基礎等級
        base_level = self.RELATION_LEVEL_MAP.get(relation_type, "chukichi")
        level = base_level

        # Step 2: 凌犯翻轉
        if ryouhan:
            level = self.RYOUHAN_LEVEL_FLIP[level]

        # Step 3: 特殊日位移
        overflow_bonus = 0
        if special_day_type:
            prev_level = level
            if special_day_type == "kanro":
                if ryouhan:
                    level = self._shift_level(level, -1)  # 凌犯中甘露 → 降級
                else:
                    level = self._shift_level(level, +1)  # 正常甘露 → 升級
            elif special_day_type == "rasetsu":
                if ryouhan:
                    level = self._shift_level(level, +1)  # 凌犯中羅刹 → 升級
                else:
                    level = self._shift_level(level, -1)  # 正常羅刹 → 降級
            elif special_day_type == "kongou":
                # 金剛峯日「宜作一切降伏法」(T21 p.398b-c)
                # 原典凌犯規則(p.391b-c)概括性適用所有日，金剛峯日亦遵循吉凶逆轉
                if ryouhan:
                    level = self._shift_level(level, -1)  # 凌犯中金剛峯 → 降級
                else:
                    level = self._shift_level(level, +1)  # 正常金剛峯 → 升級

            # 等級已在極值無法位移時，特殊日加持轉為分數溢出
            # 凌犯中不設溢出（凌犯已是極端情況，特殊日逆轉後不再疊加溢出）
            if level == prev_level and special_day_type in ("kanro", "kongou") and not ryouhan:
                overflow_bonus = 10  # 甘露/金剛峯在大吉日的額外加持
            elif level == prev_level and special_day_type == "rasetsu" and not ryouhan:
                overflow_bonus = -10  # 羅刹在凶日的額外壓制

        return level, base_level, overflow_bonus

    def _calc_daily_core(self, user_index: int, user_element: str, target_date: date, lang: str = 'zh-TW') -> dict:
        """
        每日核心計算（共用模組）

        運勢 calculate_daily_fortune() 和月曆 get_calendar_month() 共用此函數，
        確保同一天的等級和分數計算只有一條路徑。

        Args:
            user_index: 本命宿 index (0-26)
            user_element: 本命宿五行
            target_date: 查詢日期

        Returns:
            核心計算結果 dict
        """
        fortune_data = self._load_fortune_data()

        # 當日宿（修正後宿位）
        day_mansion_index = self._get_corrected_mansion_index(target_date)
        day_mansion = self.mansions_data[day_mansion_index]

        # 三九秘法：本命宿與當日宿的關係
        relation = self.get_relation_type(user_index, day_mansion_index)

        # 七曜
        weekday = target_date.weekday()
        jp_weekday = (weekday + 1) % 7
        day_info = fortune_data["weekday_elements"][str(jp_weekday)]
        day_element = day_info["element"]

        # 甘露日/金剛峯日/羅刹日
        special_day_key = (jp_weekday, day_mansion_index)
        special_day_type = self.SPECIAL_DAY_MAP.get(special_day_key)

        # 凌犯期間
        ryouhan = self.check_ryouhan_period(target_date)

        # 等級優先制
        final_level, base_level, overflow_bonus = self._determine_daily_level(
            relation["type"], ryouhan, special_day_type
        )

        # 元素相性 → 分數微調
        element_relation_type, element_bonus = self._calc_fortune_element_relation(
            user_element, day_element
        )
        element_adjustment = int(element_bonus / 2)

        # 最終分數
        fortune_score = max(30, min(100,
            self.LEVEL_DISPLAY_SCORE[final_level] + element_adjustment + overflow_bonus
        ))

        # 三期
        sanki = self.get_sanki_cycle(user_index, day_mansion_index, lang)

        return {
            "day_mansion_index": day_mansion_index,
            "day_mansion": day_mansion,
            "jp_weekday": jp_weekday,
            "day_info": day_info,
            "day_element": day_element,
            "relation": relation,
            "special_day_type": special_day_type,
            "ryouhan": ryouhan,
            "final_level": final_level,
            "base_level": base_level,
            "overflow_bonus": overflow_bonus,
            "element_relation_type": element_relation_type,
            "element_bonus": element_bonus,
            "element_adjustment": element_adjustment,
            "fortune_score": fortune_score,
            "sanki": sanki,
        }

    def calculate_daily_fortune(self, birth_date: date, target_date: date, lang: str = 'zh-TW') -> dict:
        """
        計算每日運勢

        使用三九秘法：根據「本命宿」與「當日宿」的關係決定運勢基調

        Args:
            birth_date: 出生日期
            target_date: 要查詢的日期

        Returns:
            每日運勢資料
        """
        import random

        fortune_data = self._load_fortune_data()
        mansion = self.get_mansion(birth_date)
        user_element = mansion["element"]
        user_index = mansion["index"]

        # === 核心計算（共用模組） ===
        core = self._calc_daily_core(user_index, user_element, target_date, lang)
        day_mansion_index = core["day_mansion_index"]
        day_mansion = core["day_mansion"]
        jp_weekday = core["jp_weekday"]
        day_info = core["day_info"]
        day_element = core["day_element"]
        mansion_relation = core["relation"]
        mansion_relation_type = mansion_relation["type"]
        special_day_type = core["special_day_type"]
        ryouhan = core["ryouhan"]
        final_level = core["final_level"]
        base_level = core["base_level"]
        overflow_bonus = core["overflow_bonus"]
        element_relation_type = core["element_relation_type"]
        element_bonus = core["element_bonus"]
        overall_score = core["fortune_score"]
        sanki = core["sanki"]

        # 農曆（幸運數字用）
        lunar_y, lunar_m, lunar_d, _ = self.solar_to_lunar(target_date)

        # 元素相性描述
        element_desc = self._get_fortune_element_desc(element_relation_type, lang)

        # === 計算各項運勢（從等級分數衍生 + 分類親和微調） ===
        def calc_category_score(category: str) -> int:
            cat_data = fortune_data["fortune_categories"][category]
            cat_bonus = 3 if user_element in cat_data["favorable_elements"] else 0
            day_bonus = 2 if day_element in cat_data["favorable_elements"] else 0
            return max(30, min(100, overall_score + cat_bonus + day_bonus))

        career_score = calc_category_score("career")
        love_score = calc_category_score("love")
        health_score = calc_category_score("health")
        wealth_score = calc_category_score("wealth")

        # === 六害宿判定（凌犯期間中才生效，warning flag 不影響等級） ===
        rokugai = None
        if ryouhan:
            rokugai_list = self.get_rokugai_suku(user_index)
            for rg in rokugai_list:
                if rg["mansion_index"] == day_mansion_index:
                    rokugai = {
                        "active": True,
                        "name": rg["name"],
                        "name_reading": rg["name_reading"],
                        "severity": rg["severity"],
                        "description": f"凌犯期間中の六害宿「{rg['name']}」に当たります。本命宿との関係で特に注意が必要な日です。"
                    }
                    break

        # === 特殊日資料組裝 ===
        special_day = None
        if special_day_type:
            special_day = dict(self.SPECIAL_DAY_INFO[special_day_type])
            special_day["type"] = special_day_type
            if ryouhan:
                if special_day_type in ("kanro", "kongou"):
                    special_day["ryouhan_reversed"] = True
                    special_day["original_level"] = special_day["level"]
                    special_day["level"] = "凶（凌犯逆轉）"
                elif special_day_type == "rasetsu":
                    special_day["ryouhan_reversed"] = True
                    special_day["original_level"] = special_day["level"]
                    special_day["level"] = "吉（凌犯逆轉）"
                else:
                    special_day["ryouhan_reversed"] = False
            else:
                special_day["ryouhan_reversed"] = False

        # === 各項描述（根據等級選擇，非分數門檻） ===
        def get_category_desc(category: str, ryouhan_active: bool = False) -> dict:
            """回傳 {"zh": "...", "ja": "..."} 或 {"zh": "..."}"""
            random.seed(f"{birth_date.isoformat()}{target_date.isoformat()}cat_{category}")
            if ryouhan_active:
                i18n = self._load_i18n(lang)
                descs = i18n.get('ryouhan_category_descriptions', {}).get(category, {})
                if not descs:
                    descs = self.RYOUHAN_CATEGORY_DESCRIPTIONS.get(category, {})
                desc_key = self.RYOUHAN_DESC_KEY.get(final_level, "mid_reversal")
                pool = descs.get(desc_key, [{"zh": ""}])
                return random.choice(pool)
            else:
                i18n = self._load_i18n(lang)
                descs = i18n.get('daily_category_descriptions', {}).get(category, {})
                if not descs:
                    descs = self.DAILY_CATEGORY_DESCRIPTIONS.get(category, {})
                desc_key = self.LEVEL_DESC_KEY.get(final_level, "fair")
                pool = descs.get(desc_key, [""])
                return {"zh": random.choice(pool)}

        is_ryouhan_active = ryouhan is not None
        career_descs = get_category_desc("career", is_ryouhan_active)
        love_descs = get_category_desc("love", is_ryouhan_active)
        health_descs = get_category_desc("health", is_ryouhan_active)
        wealth_descs = get_category_desc("wealth", is_ryouhan_active)
        career_desc = career_descs["zh"]
        love_desc = love_descs["zh"]
        health_desc = health_descs["zh"]
        wealth_desc = wealth_descs["zh"]
        career_desc_ja = career_descs.get("ja", "")
        love_desc_ja = love_descs.get("ja", "")
        health_desc_ja = health_descs.get("ja", "")
        wealth_desc_ja = wealth_descs.get("ja", "")

        # === 選擇建議（根據等級） ===
        random.seed(f"{birth_date.isoformat()}{target_date.isoformat()}advice")
        advice_key = self.LEVEL_ADVICE_KEY.get(final_level, "neutral")
        advice_list = self._get_fortune_advice(advice_key, lang)
        advice = random.choice(advice_list)

        # === 多因素交叉分析 ===
        compound_analysis = self._analyze_compound_factors(
            ryouhan, special_day_type, mansion_relation_type, sanki, rokugai
        )

        # === 幸運物品（每日動態計算） ===
        lucky = self._get_fortune_lucky_items(lang)

        # 方位：以當日宿元素為主，大吉日回歸本命方位
        if mansion_relation_type in ("eishin", "gyotai", "mei"):
            lucky_direction = lucky["directions"].get(user_element, lucky["directions"]["土"])
        else:
            lucky_direction = lucky["directions"].get(day_mansion["element"], lucky["directions"]["土"])

        # 顏色：以七曜元素為主，同元素日使用本命色
        if element_relation_type == "same":
            lucky_color = lucky["colors"].get(user_element, lucky["colors"]["土"])
        else:
            lucky_color = lucky["colors"].get(day_element, lucky["colors"]["土"])

        # 數字：當日宿 index + 農曆日推導，每天不同
        num1 = (day_mansion_index % 9) + 1
        num2 = ((day_mansion_index + lunar_d) % 9) + 1
        if num2 == num1:
            num2 = (num2 % 9) + 1
        lucky_numbers = [num1, num2]

        return {
            "date": target_date.isoformat(),
            "weekday": {
                "name": day_info["name"],
                "reading": day_info["reading"],
                "element": day_element,
                "planet": day_info["planet"]
            },
            "day_mansion": {
                "name_jp": day_mansion["name_jp"],
                "reading": day_mansion["reading"],
                "element": day_mansion["element"],
                "index": day_mansion_index,
                "day_fortune": self._get_day_fortune_i18n(day_mansion.get("day_fortune", {}), lang)
            },
            "your_mansion": {
                "name_jp": mansion["name_jp"],
                "reading": mansion["reading"],
                "element": user_element,
                "index": mansion["index"],
                "personality_classic": mansion.get("personality_classic", ""),
                "career_classic": mansion.get("career_classic", "")
            },
            "mansion_relation": {
                "type": mansion_relation_type,
                "name": self._relation_display_name(mansion_relation_type, lang),
                "name_jp": mansion_relation.get("name_jp", mansion_relation["name"]),
                "reading": mansion_relation.get("reading", ""),
                "description": self._seeded_choice(f"{birth_date.isoformat()}{target_date.isoformat()}rel_desc", self._get_text(lang, 'daily_fortune_descriptions', mansion_relation_type) or [mansion_relation["description"]]),
                "description_classic": mansion_relation.get("description_classic", ""),
                "description_ja": mansion_relation.get("description_ja", "")
            },
            "element_relation": {
                "type": element_relation_type,
                "type_name": self._get_element_relation_type_name(element_relation_type, lang),
                "description": element_desc
            },
            "fortune": {
                "level": final_level,
                "level_name": self._level_name(final_level, lang),
                "level_name_ja": self.LEVEL_NAMES[final_level]["ja"],
                "level_reading": self.LEVEL_NAMES[final_level]["reading"],
                "base_level": base_level,
                "overall": overall_score,
                "career": career_score,
                "love": love_score,
                "health": health_score,
                "wealth": wealth_score,
                "career_desc": career_desc,
                "love_desc": love_desc,
                "health_desc": health_desc,
                "wealth_desc": wealth_desc,
                "career_desc_ja": career_desc_ja,
                "love_desc_ja": love_desc_ja,
                "health_desc_ja": health_desc_ja,
                "wealth_desc_ja": wealth_desc_ja,
                "ryouhan_active": ryouhan is not None,
                "ryouhan_warning": "凌犯期間中，吉凶判斷可能與平時相反。表面順遂之事暗藏風險，表面困難之事反有轉機。重大決策宜延後。原典記載化解之法：品五「入灌頂及護摩，並修諸功德」（T21 p.392a-b），品三「宜修功德、持真言念誦、立道場以禳之」（T21 p.391b-c）。" if ryouhan else None,
                "ryouhan_warning_ja": "凌犯期間中のため、吉凶の判断が通常と逆転する可能性があります。原典の禳いの法：品五「灌頂に入り護摩を作し、並びに諸の功徳を修す」（T21 p.392a-b）、品三「功徳を修し、真言念誦を持し、道場を立てて以て之を禳う」（T21 p.391b-c）。重要な決断は延期をお勧めします。" if ryouhan else None,
                "effective_interpretation": self.LEVEL_INTERPRETATION.get(final_level, "neutral")
            },
            "advice": advice,
            "lucky": {
                "direction": lucky_direction["direction"],
                "direction_reading": lucky_direction["reading"],
                "color": lucky_color["color"],
                "color_reading": lucky_color["reading"],
                "color_hex": lucky_color["hex"],
                "numbers": lucky_numbers
            },
            "special_day": special_day,
            "ryouhan": ryouhan,
            "rokugai": rokugai,
            "sanki": sanki,
            "compound_analysis": compound_analysis
        }

    def calculate_monthly_fortune(self, birth_date: date, year: int, month: int, lang: str = 'zh-TW') -> dict:
        """
        計算每月運勢

        Args:
            birth_date: 出生日期
            year: 年份
            month: 月份 (1-12)

        Returns:
            每月運勢資料
        """
        import random
        from datetime import timedelta

        fortune_data = self._load_fortune_data()
        mansion = self.get_mansion(birth_date)
        user_index = mansion["index"]
        user_element = mansion["element"]

        # 取得該月的月宿（使用月宿傍通曆）
        mid_date = date(year, month, 15)
        _, lunar_month_for_mansion, _, _ = self.solar_to_lunar(mid_date)
        month_mansion_index = self.MONTH_START_MANSION.get(lunar_month_for_mansion, 0)
        month_mansion = self.mansions_data[month_mansion_index]
        month_mansion_elem = month_mansion["element"]

        # 本命宿 vs 月宿關係
        relation = self.get_relation_type(user_index, month_mansion_index)

        # 月份主題（供回傳用）
        month_theme = self._get_fortune_monthly_theme(month, lang)
        theme_element = month_theme.get("element_boost", "土")

        # 計算該月天數
        first_day = date(year, month, 1)
        if month == 12:
            next_month_first = date(year + 1, 1, 1)
        else:
            next_month_first = date(year, month + 1, 1)
        days_in_month = (next_month_first - first_day).days

        # 收集所有日運資料
        daily_result = self._collect_daily_data(birth_date, first_day, days_in_month, lang)
        all_daily = daily_result["all_daily"]
        ryouhan_count = daily_result["ryouhan_count"]
        special_days_in_month = daily_result["special_days"]
        dark_week_count = daily_result["dark_week_count"]

        # 月整體分數 = 每日分數平均（與週分數算法一致）
        ryouhan_ratio = ryouhan_count / days_in_month if days_in_month > 0 else 0
        daily_avg = round(sum(d["score"] for d in all_daily) / len(all_daily)) if all_daily else 60
        base_score = max(35, min(100, daily_avg))

        # 從平均分數反推月等級
        if base_score >= 90:
            month_level = "daikichi"
        elif base_score >= 75:
            month_level = "kichi"
        elif base_score >= 60:
            month_level = "chukichi"
        elif base_score >= 45:
            month_level = "shokyo"
        else:
            month_level = "kyo"

        # 各項運勢（基於元素親和，非隨機數）
        def calc_monthly_category(category: str) -> int:
            cat_data = fortune_data["fortune_categories"][category]
            cat_bonus = 8 if user_element in cat_data["favorable_elements"] else 0
            month_elem_bonus = 5 if month_mansion_elem in cat_data["favorable_elements"] else 0
            return max(30, min(100, base_score + cat_bonus + month_elem_bonus))

        # 按三期サイクル分組
        weekly = self._build_monthly_periods(all_daily, fortune_data, lang)

        # 月警告彙整
        month_warnings = self._build_month_warnings(ryouhan_count, dark_week_count, special_days_in_month)

        # 月度策略分析
        monthly_strategy = self._generate_monthly_strategy(weekly, all_daily, ryouhan_count, days_in_month)

        return {
            "year": year,
            "month": month,
            "lunar_month": lunar_month_for_mansion,
            "month_mansion": {
                "name_jp": month_mansion["name_jp"],
                "reading": month_mansion["reading"],
                "index": month_mansion_index,
                "element": month_mansion["element"]
            },
            "your_mansion": {
                "name_jp": mansion["name_jp"],
                "reading": mansion["reading"],
                "element": user_element,
                "index": user_index
            },
            "relation": {
                "type": relation["type"],
                "name": self._relation_display_name(relation["type"], lang),
                "name_jp": relation.get("name_jp", relation["name"]),
                "reading": relation.get("reading", ""),
                "description": self._seeded_choice(f"{birth_date.isoformat()}{year}{month}rel_desc", self._get_text(lang, 'monthly_fortune_descriptions', relation["type"]) or [relation["description"]])
            },
            "theme": {
                "title": month_theme.get("theme", ""),
                "focus": month_theme.get("focus", ""),
                "element_boost": theme_element,
                "description": self._seeded_choice(f"{birth_date.isoformat()}{year}{month}theme_desc", self._get_text(lang, 'monthly_theme_descriptions', relation["type"]) or ["本月能量平穩，按照自己的步調前進即可。"])
            },
            "fortune": {
                "level": month_level,
                "level_name": self._level_name(month_level, lang),
                "level_name_ja": self.LEVEL_NAMES[month_level]["ja"],
                "level_reading": self.LEVEL_NAMES[month_level]["reading"],
                "overall": base_score,
                "career": calc_monthly_category("career"),
                "love": calc_monthly_category("love"),
                "health": calc_monthly_category("health"),
                "wealth": calc_monthly_category("wealth")
            },
            "ryouhan_info": {
                "affected_days": ryouhan_count,
                "total_days": days_in_month,
                "ratio": round(ryouhan_ratio, 2)
            } if ryouhan_count > 0 else None,
            "month_warnings": month_warnings,
            "special_days": special_days_in_month,
            "weekly": weekly,
            "strategy": monthly_strategy,
            "advice": self._seeded_choice(f"{birth_date.isoformat()}{year}{month}advice", self._get_text(lang, 'monthly_fortune_advice', relation["type"]) or [self._relation_display_name(relation['type'], lang)])
        }

    def _collect_daily_data(self, birth_date: date, first_day: date, days_in_month: int, lang: str) -> dict:
        """收集一個月內所有日運資料"""
        from datetime import timedelta
        all_daily = []
        ryouhan_count = 0
        special_days = []
        dark_week_count = 0

        for d in range(days_in_month):
            day_date = first_day + timedelta(days=d)
            daily_fortune = self.calculate_daily_fortune(birth_date, day_date, lang=lang)

            is_ryouhan = daily_fortune.get("ryouhan") is not None
            special_day = daily_fortune.get("special_day")
            is_dark = daily_fortune.get("sanki", {}).get("is_dark_week", False)

            if is_ryouhan:
                ryouhan_count += 1
            if special_day:
                special_days.append({
                    "date": day_date.isoformat(),
                    "type": special_day.get("type", ""),
                    "name": special_day.get("name", "")
                })
            if is_dark:
                dark_week_count += 1

            sanki = daily_fortune.get("sanki", {})
            all_daily.append({
                "date": day_date.isoformat(),
                "weekday": daily_fortune["weekday"]["name"],
                "score": daily_fortune["fortune"]["overall"],
                "special_day": special_day.get("name") if special_day else None,
                "ryouhan_active": is_ryouhan,
                "is_dark_week": is_dark,
                "sanki_period_index": sanki.get("period_index", 1),
                "sanki_period": sanki.get("period", "躍動の週"),
                "sanki_day_in_period": sanki.get("day_in_period", 1),
                "sanki_day_type": sanki.get("day_type", ""),
            })

        return {
            "all_daily": all_daily,
            "ryouhan_count": ryouhan_count,
            "special_days": special_days,
            "dark_week_count": dark_week_count,
        }

    def _build_monthly_periods(self, all_daily: list, fortune_data: dict, lang: str) -> list:
        """將每日資料按三期サイクル分組成 weekly 結構"""
        periods: list[dict] = []
        current_group: dict | None = None

        for d in all_daily:
            period_idx = d["sanki_period_index"]
            if current_group is None or current_group["period_index"] != period_idx:
                if current_group is not None:
                    periods.append(current_group)
                current_group = {
                    "period_index": period_idx,
                    "period_name": d["sanki_period"],
                    "days": [d]
                }
            else:
                current_group["days"].append(d)

        if current_group is not None:
            periods.append(current_group)

        weekly = []
        for seq, group in enumerate(periods, 1):
            days = group["days"]
            score = max(40, min(100, round(sum(d["score"] for d in days) / len(days))))

            start_date = date.fromisoformat(days[0]["date"])
            jp_weekday = (start_date.weekday() + 1) % 7
            week_element = fortune_data["weekday_elements"].get(str(jp_weekday), {}).get("element", "土")
            best_focus = "career"
            for cat in ["career", "love", "health", "wealth"]:
                if week_element in fortune_data["fortune_categories"][cat]["favorable_elements"]:
                    best_focus = cat
                    break

            warnings = []
            ryouhan_days = sum(1 for d in days if d["ryouhan_active"])
            dark_days = sum(1 for d in days if d["is_dark_week"])
            specials = [d for d in days if d["special_day"]]
            if ryouhan_days > 0:
                warnings.append(f"凌犯期間 {ryouhan_days} 日")
            if dark_days > 0:
                warnings.append(f"暗黒の一週間 {dark_days} 日")
            for sp in specials:
                warnings.append(f"{sp['date'][-5:]} {sp['special_day']}")

            weekly.append({
                "week": seq,
                "period_index": group["period_index"],
                "period_name": group["period_name"],
                "period_reading": self.SANKI_CYCLE[group["period_index"] - 1]["reading"],
                "week_start": days[0]["date"],
                "week_end": days[-1]["date"],
                "days_count": len(days),
                "score": score,
                "focus": self._get_fortune_category_name(best_focus, lang),
                "has_dark_week": dark_days > 0,
                "daily_overview": days,
                "warnings": warnings,
            })
        return weekly

    def _build_month_warnings(self, ryouhan_count: int, dark_week_count: int, special_days: list) -> list:
        """組裝月度警告訊息"""
        warnings = []
        if ryouhan_count > 0:
            warnings.append(f"本月有 {ryouhan_count} 天處於凌犯期間，吉凶逆轉需特別留意（{RYOUHAN_TAG}）")
        if dark_week_count > 0:
            warnings.append(f"本月有 {dark_week_count} 天處於暗黒の一週間，判斷力下降宜保守行事（{DARK_WEEK_TAG}）")
        kanro_count = sum(1 for s in special_days if s["type"] == "kanro")
        rasetsu_count = sum(1 for s in special_days if s["type"] == "rasetsu")
        kongou_count = sum(1 for s in special_days if s["type"] == "kongou")
        if kanro_count > 0:
            warnings.append(f"甘露日 {kanro_count} 天")
        if rasetsu_count > 0:
            warnings.append(f"羅刹日 {rasetsu_count} 天")
        if kongou_count > 0:
            warnings.append(f"金剛峯日 {kongou_count} 天")
        return warnings

    def calculate_weekly_fortune(self, birth_date: date, target_date: date, lang: str = 'zh-TW') -> dict:
        """
        計算週運勢（滾動視窗）

        以 target_date 為中心，返回：
        - 昨天（1天）
        - 今天（target_date）
        - 未來 6 天
        共 8 天的運勢，更直觀的「本週」概念

        Args:
            birth_date: 出生日期
            target_date: 中心日期（通常是今天）

        Returns:
            週運勢資料
        """
        import random
        from datetime import timedelta

        fortune_data = self._load_fortune_data()
        mansion = self.get_mansion(birth_date)
        user_index = mansion["index"]
        user_element = mansion["element"]

        # 滾動視窗：昨天 + 今天 + 未來6天 = 8天
        yesterday = target_date - timedelta(days=1)
        week_end = target_date + timedelta(days=6)

        # 取得 target_date 的七曜元素
        weekday = target_date.weekday()
        jp_weekday = (weekday + 1) % 7
        day_info = fortune_data["weekday_elements"].get(str(jp_weekday), {
            "name": "月曜日", "reading": "げつようび", "element": "月", "planet": "月"
        })
        center_element = day_info["element"]

        # 計算元素關係
        relation_type, base_bonus = self._calc_fortune_element_relation(user_element, center_element)
        relation_desc = self._get_fortune_element_desc(relation_type, lang)

        # 收集每日運勢（8天）+ 特殊日/凌犯/暗黒統計
        daily_overview = []
        week_warnings = []
        ryouhan_count = 0
        dark_week_count = 0
        special_day_entries = []

        for day_offset in range(-1, 7):
            day_date = target_date + timedelta(days=day_offset)
            daily_fortune = self.calculate_daily_fortune(birth_date, day_date, lang=lang)

            is_ryouhan = daily_fortune.get("ryouhan") is not None
            special_day = daily_fortune.get("special_day")
            is_dark = daily_fortune.get("sanki", {}).get("is_dark_week", False)

            if is_ryouhan:
                ryouhan_count += 1
            if special_day:
                special_day_entries.append({
                    "date": day_date.isoformat(),
                    "name": special_day.get("name", "")
                })
            if is_dark:
                dark_week_count += 1

            daily_overview.append({
                "date": day_date.isoformat(),
                "weekday": daily_fortune["weekday"]["name"],
                "score": daily_fortune["fortune"]["overall"],
                "level": daily_fortune["fortune"].get("level", ""),
                "is_today": day_offset == 0,
                "is_yesterday": day_offset == -1,
                "special_day": special_day.get("name") if special_day else None,
                "ryouhan_active": is_ryouhan,
                "is_dark_week": is_dark
            })

        # 週整體分數 = 8 天每日分數平均（日分數已從等級映射，自然傳遞）
        overall_score = round(sum(d["score"] for d in daily_overview) / len(daily_overview))
        overall_score = max(30, min(100, overall_score))

        # 各項運勢（以日運平均為基礎，與月運算法一致）
        def calc_weekly_category(category: str) -> int:
            cat_data = fortune_data["fortune_categories"][category]
            cat_bonus = 6 if user_element in cat_data["favorable_elements"] else 0
            day_bonus = 4 if center_element in cat_data["favorable_elements"] else 0
            return max(30, min(100, overall_score + cat_bonus + day_bonus))

        career_score = calc_weekly_category("career")
        love_score = calc_weekly_category("love")
        health_score = calc_weekly_category("health")
        wealth_score = calc_weekly_category("wealth")

        # 週警告彙整
        if ryouhan_count > 0:
            week_warnings.append(f"凌犯期間 {ryouhan_count} 日（{RYOUHAN_TAG}）")
        if dark_week_count > 0:
            week_warnings.append(f"暗黒の一週間 {dark_week_count} 日（{DARK_WEEK_TAG}）")
        for sp in special_day_entries:
            week_warnings.append(f"{sp['date'][-5:]} {sp['name']}")

        # 選擇建議（根據平均分數反推等級）
        random.seed(f"{birth_date.isoformat()}{target_date.isoformat()}weekly_advice")
        if overall_score >= 83:
            advice_list = self._get_fortune_advice("excellent", lang)
        elif overall_score >= 68:
            advice_list = self._get_fortune_advice("good", lang)
        elif overall_score >= 53:
            advice_list = self._get_fortune_advice("neutral", lang)
        elif overall_score >= 40:
            advice_list = self._get_fortune_advice("caution", lang)
        else:
            advice_list = self._get_fortune_advice("challenging", lang)

        advice = random.choice(advice_list)

        # 幸運物品
        lucky = self._get_fortune_lucky_items(lang)
        lucky_direction = lucky["directions"].get(center_element, lucky["directions"]["土"])
        lucky_color = lucky["colors"].get(center_element, lucky["colors"]["土"])

        # 各項提示
        category_tips = {}
        i18n = self._load_i18n(lang)
        for cat in ["career", "love", "health"]:
            cat_tips = i18n.get('weekly_category_tips', {}).get(cat, {})
            if not cat_tips:
                cat_tips = self.WEEKLY_CATEGORY_TIPS.get(cat, {})
            tip_key = relation_type if relation_type in cat_tips else "neutral"
            random.seed(f"{birth_date.isoformat()}{target_date.isoformat()}tip_{cat}")
            category_tips[cat] = random.choice(cat_tips.get(tip_key, [""]))

        return {
            "center_date": target_date.isoformat(),
            "week_start": yesterday.isoformat(),
            "week_end": week_end.isoformat(),
            "today_element": {
                "name": day_info["name"],
                "reading": day_info["reading"],
                "element": center_element,
                "planet": day_info["planet"]
            },
            "your_mansion": {
                "name_jp": mansion["name_jp"],
                "reading": mansion["reading"],
                "element": user_element,
                "index": user_index
            },
            "element_relation": {
                "type": relation_type,
                "type_name": self._get_element_relation_type_name(relation_type, lang),
                "description": relation_desc
            },
            "fortune": {
                "overall": overall_score,
                "career": career_score,
                "love": love_score,
                "health": health_score,
                "wealth": wealth_score
            },
            "daily_overview": daily_overview,
            "week_warnings": week_warnings,
            "advice": advice,
            "focus": self._seeded_choice(f"{birth_date.isoformat()}{target_date.isoformat()}weekly_focus", self._get_text(lang, 'weekly_fortune_focus', relation_type) or self.WEEKLY_FORTUNE_FOCUS.get("neutral", [""])),
            "category_tips": category_tips,
            "lucky": {
                "direction": lucky_direction["direction"],
                "direction_reading": lucky_direction["reading"],
                "color": lucky_color["color"],
                "color_reading": lucky_color["reading"],
                "color_hex": lucky_color["hex"]
            }
        }

    # 九曜流年法：9 年循環（寺院傳承，非 T21n1299 原典）
    # 出處：日本真言宗寺院（放生寺/大聖院/岡寺）的九曜星供法會傳承
    # 九曜（Navagraha）源自印度天文學，在宿曜道實踐中與 T21n1299 七曜體系結合
    # 數え年 1 歲 = 羅喉星，每年順推
    # 注意：base_score 為各星的參考分數（前端展示用），
    #       年運 overall 實際使用 KUYOU_LEVEL_MAP（大吉=85/半吉=65/末吉=50/大凶=35）。
    KUYOU_STARS = [
        {
            "name": "羅喉星", "reading": "らごうせい",
            "level": "大凶", "fortune_name": "潜運",
            "element": None, "base_score": 48,
            "buddha": "不動明王",
            "description": "T21 品八記載羅喉為「蝕神」（p.399a），遮蔽日月光明。九曜循環流年法（寺院傳承：放生寺/大聖院/岡寺）判定為大凶「潜運」年。蝕神當值，外在機運被遮蔽，做什麼都容易卡住。不是你能力不夠，是時運走到這裡。這一年的重點：不主動出擊、不衝動換工作或大額投資。把想做的事記下來，等明年土曜星年再行動。減少應酬、保存體力，用這段時間觀察和準備。忍住不動比亂動更需要實力。",
            "yearly_advice": "羅喉星為蝕神（T21 品八 p.399a），九曜循環流年法（寺院傳承）判定大凶。蝕神遮光，外在機運低迷——不主動出擊、不衝動換工作、不做大額投資。把想做的事記下來等土曜星年再動。減少應酬、保存體力，用這段時間觀察局勢和累積實力。羅喉年過後是土曜半吉→水曜末吉→金曜半吉，耐心等待回升。"
        },
        {
            "name": "土曜星", "reading": "どようせい",
            "level": "半吉", "fortune_name": "開運",
            "element": "土", "base_score": 62,
            "buddha": "聖觀音",
            "description": "T21 品八記載七曜各主一元素（p.399a），土曜屬土，性質沉穩遲緩。九曜循環流年法（寺院傳承）判定為半吉「開運」年——從羅喉星大凶年後開始回升。整體趨勢往上，但速度慢，急不來。身體容易出小狀況，夏秋之間留意健康。這一年適合打基礎：整理財務、建立習慣、規劃下一步。不是衝刺的時機，是準備起跑的時機。穩住腳步，後面三年會越來越順。"
        },
        {
            "name": "水曜星", "reading": "すいようせい",
            "level": "末吉", "fortune_name": "喜運",
            "element": "水", "base_score": 58,
            "buddha": "彌勒菩薩",
            "description": "T21 品八記載七曜各主一元素（p.399a），水曜屬水，性質流動多變。九曜循環流年法（寺院傳承）判定為末吉「喜運」年。運勢不差但不穩定，心思容易比實際狀況更紛亂。春夏低調行事，少做承諾；秋冬明顯好轉。拿不定主意的事不要自己悶著想，找有經驗的人問一問。水性流動，這一年的變化多，但大方向是往好的走。"
        },
        {
            "name": "金曜星", "reading": "きんようせい",
            "level": "半吉", "fortune_name": "平運",
            "element": "金", "base_score": 63,
            "buddha": "阿彌陀如來",
            "description": "T21 品八記載七曜各主一元素（p.399a），金曜屬金，性質肅殺收斂。九曜循環流年法（寺院傳承）判定為半吉「平運」年。吉凶參半，好壞交織。人際關係是今年最需要注意的——工作上可能出現意料之外的變動。金性主收斂，這一年適合整理而非擴張：盤點人脈、清理不必要的關係、聽從專業建議。困難的處境反而能讓你分辨誰是真正幫你的人。"
        },
        {
            "name": "日曜星", "reading": "にちようせい",
            "level": "大吉", "fortune_name": "盛運",
            "element": "日", "base_score": 82,
            "buddha": "千手觀音",
            "description": "T21 品八記載「日曜為天體之首」（p.399a），九曜中最尊貴的一星。九曜循環流年法（寺院傳承）判定為大吉「盛運」年。做什麼都順、財運旺、聲望上升。這一年該做的事：升遷該爭取就爭取、案子該推就推、人脈該經營就經營。積極行動會帶來超出預期的回報。唯一要注意：越順利越要謙虛。把成果轉化為長期資產（技能、人脈、存款），別花在虛榮上。好運不會年年有，趁這一年打好底。"
        },
        {
            "name": "火曜星", "reading": "かようせい",
            "level": "大凶", "fortune_name": "休運",
            "element": "火", "base_score": 42,
            "buddha": "虛空藏菩薩",
            "description": "T21 品八記載七曜各主一元素（p.399a），火曜屬火，性質急烈。九曜循環流年法（寺院傳承）判定為大凶「休運」年。火性急躁，這一年最忌衝動。人際容易起衝突、工作容易出狀況，很多問題的根源是溝通不順。控制情緒是今年最重要的事——想發火的時候先離開現場，十分鐘後再回應。不要主動跳槽或大幅改變現狀，守住手上的就好。下一年仍是計都星大凶年，但之後就是月曜、木曜連續兩年大吉，熬過低谷就是上升期。",
            "yearly_advice": "火曜屬火、性質急烈（T21 品八 p.399a），九曜循環流年法（寺院傳承）判定大凶。火性年最忌衝動——想發火先離開現場十分鐘再回應，想跳槽先擱七天再決定。守住手上的工作和關係就好，不要主動改變現狀。下一年計都星仍是大凶，但再撐過去就是月曜大吉→木曜大吉的連續上升期。"
        },
        {
            "name": "計都星", "reading": "けいとせい",
            "level": "大凶", "fortune_name": "滞運",
            "element": None, "base_score": 45,
            "buddha": "釋迦如來",
            "description": "T21 品八記載計都為「蝕神」（p.399a），與羅喉同為遮蔽之星。九曜循環流年法（寺院傳承：放生寺/大聖院/岡寺）判定為大凶「滞運」年。付出和回報不成正比，事情的進展比預期慢。春季三個月特別需要耐心，秋天之後逐漸好轉。這不是能力問題，是時運節奏走到這裡。調整期望、減少冒險、守住現有成果。趁這段減速期盤點資源、整理方向，為下一年月曜星大吉年做準備。",
            "yearly_advice": "計都為蝕神（T21 品八 p.399a），九曜循環流年法（寺院傳承）判定大凶。付出和回報不成正比，事情進展比預期慢。春季三個月特別需要耐心，秋天逐漸好轉。調整期望、減少冒險、守住現有成果。計都年是九曜大凶的最後一年——撐過去就是月曜星大吉年，黎明前最後一段黑暗。"
        },
        {
            "name": "月曜星", "reading": "げつようせい",
            "level": "大吉", "fortune_name": "進運",
            "element": "月", "base_score": 80,
            "buddha": "勢至菩薩",
            "description": "T21 品八記載「月曜為夜之主」（p.399a），掌管夜間與陰性能量。九曜循環流年法（寺院傳承）判定為大吉「進運」年。人脈和機運同時到位，工作上有貴人拉拔。月性柔和，這一年的好運不像日曜星那麼張揚，但更加穩定持久。適合拓展人脈、承擔更大責任、經營長期關係。把握每一個被引薦的機會，主動回應善意。好運持續整年，趁勢把成果轉化為長期根基。"
        },
        {
            "name": "木曜星", "reading": "もくようせい",
            "level": "大吉", "fortune_name": "吉運",
            "element": "木", "base_score": 80,
            "buddha": "藥師如來",
            "description": "T21 品八記載七曜各主一元素（p.399a），木曜屬木，性質生長發展。九曜循環流年法（寺院傳承）判定為大吉「吉運」年。木性向上，做什麼都容易成長。婚姻運好、家庭安泰、私人生活充實。開始新關係、搬家、轉換跑道，今年的選擇容易帶來好結果。但好運不等於不用努力——吉年鬆懈是最大的浪費。九曜循環走完木曜星之後就是羅喉星大凶年，趁這一年把該做的做完。"
        }
    ]

    def calculate_yearly_fortune(self, birth_date: date, year: int, lang: str = 'zh-TW') -> dict:
        """
        計算每年運勢（九曜流年法）

        根據數え年計算當年的九曜星，結合本命宿元素推導年運。

        Args:
            birth_date: 出生日期
            year: 年份

        Returns:
            每年運勢資料
        """
        import random

        fortune_data = self._load_fortune_data()
        mansion = self.get_mansion(birth_date)
        user_index = mansion["index"]
        user_element = mansion["element"]

        # === 九曜流年法 ===
        kazoe_age = year - birth_date.year + 1
        star_index = (kazoe_age - 1) % 9
        star = self.KUYOU_STARS[star_index]
        star_element = star["element"]

        # 九曜等級 → 顯示分數（KUYOU_LEVEL_MAP）
        kuyou_level_score = self.KUYOU_LEVEL_MAP.get(star["level"], 50)

        # 九曜星與本命元素的關係（僅影響分類，不影響整體等級）
        if star_element:
            star_relation, star_bonus = self._calc_fortune_element_relation(user_element, star_element)
        else:
            # 羅喉星/計都星無元素，使用 conflicting 作為預設
            star_relation = "conflicting"
            star_bonus = -10

        base_score = kuyou_level_score

        warnings = []

        # 九曜年運對月趨勢的加持（大吉年底氣高，大凶年全面壓低）
        KUYOU_MONTHLY_MODIFIER = {
            "大吉": 8,
            "半吉": 3,
            "末吉": 0,
            "大凶": -8,
        }
        kuyou_modifier = KUYOU_MONTHLY_MODIFIER.get(star["level"], 0)

        # 計算每月趨勢（月宿關係 + 九曜年運加持）
        monthly_trend = []
        for m in range(1, 13):
            # 取得該月月宿（農曆月份）
            mid_date = date(year, m, 15)
            _, lunar_month_for_trend, _, _ = self.solar_to_lunar(mid_date)
            month_mansion_idx = self.MONTH_START_MANSION.get(lunar_month_for_trend, 0)

            # 本命宿 vs 月宿關係（供下游 strategy 使用）
            month_relation = self.get_relation_type(user_index, month_mansion_idx)

            if m == 12:
                days_in_m = (date(year + 1, 1, 1) - date(year, m, 1)).days
            else:
                days_in_m = (date(year, m + 1, 1) - date(year, m, 1)).days

            # 逐日計算日運分數，與月運算法一致
            daily_scores = []
            ryouhan_count = 0
            sd_counts = {"kanro": 0, "kongou": 0, "rasetsu": 0}
            for d in range(1, days_in_m + 1):
                try:
                    check_date = date(year, m, d)
                    daily = self.calculate_daily_fortune(birth_date, check_date, lang=lang)
                    daily_scores.append(daily["fortune"]["overall"])

                    if daily.get("ryouhan") is not None:
                        ryouhan_count += 1

                    # 統計特殊日數量（甘露/金剛峯/羅刹）
                    sp = daily.get("special_day")
                    if sp:
                        sp_type = sp.get("type", "")
                        if sp_type in sd_counts:
                            sd_counts[sp_type] += 1
                except Exception:
                    pass

            ryouhan_ratio = ryouhan_count / days_in_m if days_in_m > 0 else 0
            month_score = round(sum(daily_scores) / len(daily_scores)) if daily_scores else 60
            month_score = max(35, min(100, month_score))

            monthly_trend.append({
                "month": m,
                "score": month_score,
                "relation_type": month_relation["type"],
                "ryouhan_ratio": round(ryouhan_ratio, 2),
                "special_day_counts": sd_counts
            })

        # 找出機會月份（分數最高的 3 個月）
        sorted_months = sorted(monthly_trend, key=lambda x: x["score"], reverse=True)
        opportunities = []
        strat_i18n = self._load_strategy_i18n(lang)
        opportunity_details = strat_i18n.get("opportunity_details", {})
        opp_default = strat_i18n.get("opportunity_default", "把握機會積極行動")
        opp_format = strat_i18n.get("opportunity_format", "{month}月（運勢分數 {score}）：{detail}")
        for m in sorted_months[:3]:
            theme = self._get_fortune_monthly_theme(m["month"], lang)
            focus = theme.get("focus", "發展")
            detail = opportunity_details.get(focus, opp_default)
            opportunities.append(opp_format.format(month=m['month'], score=m['score'], detail=detail))

        # 找出需注意的月份（分數最低的）
        warn_tpl = strat_i18n.get("warning_low_score", "{month}月運勢較低（{score}分），{tag}避免重大投資或簽約")
        worst_months = sorted(monthly_trend, key=lambda x: x["score"])[:2]
        for wm in worst_months:
            if wm["score"] < 55:
                warnings.append(warn_tpl.format(month=wm['month'], score=wm['score'], tag=DARK_WEEK_TAG))

        # overall 直接使用等級分數，不含元素微調（等級決定整體，元素只影響分類）
        base_score = max(35, min(95, base_score))

        # 各項運勢（等級分數 + 元素親和微調）
        star_element_for_cat = star_element if star_element else "土"

        def calc_yearly_category(category: str) -> int:
            cat_data = fortune_data["fortune_categories"][category]
            cat_bonus = 10 if user_element in cat_data["favorable_elements"] else 0
            year_boost = 5 if star_element_for_cat in cat_data["favorable_elements"] else 0
            star_adj = star_bonus // 4 if star_element else 0  # 九曜元素微調
            return max(35, min(100, base_score + cat_bonus + year_boost + star_adj))

        # 描述用的元素關係 key（九曜吉凶等級優先於元素關係）
        # 大凶：一律使用專屬 kyo 描述（務實安撫導向，非元素摩擦）
        # 末吉：正面元素降為 weakening
        # 大吉：負面/中性元素強制升為 generating
        # 半吉：衝突元素緩和為 weakening
        desc_relation = star_relation
        if star["level"] == "大凶":
            desc_relation = "kyo"
        elif star["level"] == "末吉":
            if star_relation in ("same", "generating"):
                desc_relation = "weakening"
        elif star["level"] == "大吉":
            if star_relation in ("neutral", "conflicting", "weakening"):
                desc_relation = "generating"
        elif star["level"] == "半吉":
            if star_relation == "conflicting":
                desc_relation = "weakening"

        # 載入九曜星 i18n 翻譯
        kuyou_i18n = self._load_kuyou_i18n(lang)
        star_key = self.KUYOU_STAR_KEYS[star_index]
        star_i18n = kuyou_i18n.get("stars", {}).get(star_key, {})

        # 年度建議（大凶年用星的專屬建議，非大凶年用五行關係通用建議）
        if star["level"] == "大凶" and star_i18n.get("yearly_advice"):
            advice = star_i18n["yearly_advice"]
        else:
            i18n_yearly = self._load_i18n(lang)
            i18n_advice = i18n_yearly.get('yearly_fortune_advice', {})
            if not i18n_advice:
                i18n_advice = self.YEARLY_FORTUNE_ADVICE
            advice_key = desc_relation if desc_relation in i18n_advice else "neutral"
            random.seed(f"{birth_date.isoformat()}{year}advice")
            advice = random.choice(i18n_advice[advice_key])

        # 年度主題：使用九曜星的 fortune_name 作為標題
        i18n_yearly = self._load_i18n(lang)
        i18n_theme = i18n_yearly.get('yearly_theme_descriptions', {})
        if not i18n_theme:
            i18n_theme = self.YEARLY_THEME_DESCRIPTIONS
        theme_key = desc_relation if desc_relation in i18n_theme else "neutral"
        random.seed(f"{birth_date.isoformat()}{year}theme")
        theme_description = random.choice(i18n_theme[theme_key])

        # 大凶年不覆蓋 theme（星的專屬描述已在 kuyou_star.description 中）
        # 通用 kyo theme 文字提供不同角度的建議，避免與 description/advice 重複

        # 各項分述
        category_descriptions = {}
        i18n_cat = i18n_yearly.get('yearly_category_descriptions', {})
        for cat in ["career", "love", "health", "wealth"]:
            cat_data = i18n_cat.get(cat, {})
            if not cat_data:
                cat_data = self.YEARLY_CATEGORY_DESCRIPTIONS.get(cat, {})
            cat_key = desc_relation if desc_relation in cat_data else "neutral"
            random.seed(f"{birth_date.isoformat()}{year}catdesc_{cat}")
            cat_descs = cat_data.get(cat_key, [""])
            category_descriptions[cat] = random.choice(cat_descs)

        # 年度策略分析
        strategy = self._generate_yearly_strategy(monthly_trend, star["level"], birth_date, year, lang=lang)

        # 月趨勢加入動態提示（取代固定 tip）
        for item in monthly_trend:
            item["tip"] = strategy["dynamic_tips"].get(item["month"], "")

        return {
            "year": year,
            "kuyou_star": {
                "name": star["name"],
                "reading": star["reading"],
                "level": star["level"],
                "fortune_name": star_i18n.get("fortune_name", star["fortune_name"]),
                "element": star_element,
                "buddha": star_i18n.get("buddha", star["buddha"]),
                "description": star_i18n.get("description", star["description"]),
                "kazoe_age": kazoe_age
            },
            "your_mansion": {
                "name_jp": mansion["name_jp"],
                "reading": mansion["reading"],
                "element": user_element,
                "index": user_index
            },
            "fortune": {
                "overall": base_score,
                "career": calc_yearly_category("career"),
                "love": calc_yearly_category("love"),
                "health": calc_yearly_category("health"),
                "wealth": calc_yearly_category("wealth")
            },
            "theme": {
                "title": strat_i18n.get("theme_title", "{fortune_name}之年").format(
                    fortune_name=star_i18n.get("fortune_name", star["fortune_name"])
                ),
                "description": theme_description
            },
            "category_descriptions": category_descriptions,
            "monthly_trend": monthly_trend,
            "opportunities": opportunities,
            "warnings": warnings,
            "advice": advice,
            "strategy": strategy
        }

    def _generate_yearly_strategy(self, monthly_trend: list, _kuyou_level: str, birth_date: date, year: int, lang: str = 'zh-TW') -> dict:
        """年度趨吉避凶策略分析"""
        strat_i18n = self._load_strategy_i18n(lang)
        return {
            "safe_havens": self._find_safe_havens(monthly_trend, strat_i18n),
            "best_months": self._find_best_months(monthly_trend, strat_i18n),
            "caution_months": self._find_caution_months(monthly_trend, strat_i18n),
            "ryouhan_outlook": self._build_ryouhan_outlook(monthly_trend, strat_i18n),
            "yearly_rhythm": self._analyze_yearly_rhythm(monthly_trend, strat_i18n),
            "dynamic_tips": {m["month"]: self._generate_dynamic_tip(m, strat_i18n) for m in monthly_trend}
        }

    def _classify_streak_cluster(self, cluster_months: list) -> str | None:
        """判斷連續高分月份的集群類型"""
        eishin_count = sum(1 for x in cluster_months if x["relation_type"] == "eishin")
        gyotai_count = sum(1 for x in cluster_months if x["relation_type"] == "gyotai")
        if eishin_count >= len(cluster_months) // 2:
            return "eishin_cluster"
        if gyotai_count >= len(cluster_months) // 2:
            return "gyotai_cluster"
        return None

    def _append_safe_haven(self, safe_havens: list, monthly_trend: list, start: int, end: int, strat_i18n: dict):
        """將一段連續高分區段加入避風港列表"""
        if end - start + 1 < 2:
            return
        cluster_months = [x for x in monthly_trend if start <= x["month"] <= end]
        cluster_type = self._classify_streak_cluster(cluster_months)
        safe_havens.append({
            "start_month": start,
            "end_month": end,
            "avg_score": round(sum(x["score"] for x in cluster_months) / len(cluster_months)),
            "cluster_type": cluster_type,
            "description": self._safe_haven_description(start, end, cluster_type, strat_i18n)
        })

    def _find_safe_havens(self, monthly_trend: list, strat_i18n: dict) -> list:
        """找出連續 2+ 個月 score >= 65 的避風港區段"""
        safe_havens = []
        streak_start = None
        for m in monthly_trend:
            if m["score"] >= 65:
                if streak_start is None:
                    streak_start = m["month"]
            else:
                if streak_start is not None:
                    streak_end = monthly_trend[monthly_trend.index(m) - 1]["month"]
                    self._append_safe_haven(safe_havens, monthly_trend, streak_start, streak_end, strat_i18n)
                    streak_start = None
        if streak_start is not None:
            self._append_safe_haven(safe_havens, monthly_trend, streak_start, monthly_trend[-1]["month"], strat_i18n)
        return safe_havens

    def _find_best_months(self, monthly_trend: list, strat_i18n: dict) -> list:
        """找出 score top 3 且無凌犯的最佳月份"""
        candidates = [m for m in monthly_trend if m["ryouhan_ratio"] == 0]
        if len(candidates) < 3:
            candidates = sorted(monthly_trend, key=lambda x: (-x["score"], x["ryouhan_ratio"]))
        else:
            candidates = sorted(candidates, key=lambda x: -x["score"])
        return [{
            "month": m["month"],
            "score": m["score"],
            "relation_type": m["relation_type"],
            "description": self._best_month_description(m, strat_i18n)
        } for m in candidates[:3]]

    def _find_caution_months(self, monthly_trend: list, strat_i18n: dict) -> list:
        """找出需要警戒的月份（凌犯 >= 50% 或安壊低分）"""
        caution_reasons_i18n = strat_i18n.get("caution_reasons", {})
        caution_months = []
        for m in monthly_trend:
            reasons = []
            if m["ryouhan_ratio"] >= 0.5:
                pct = int(m["ryouhan_ratio"] * 100)
                reasons.append(caution_reasons_i18n.get("ryouhan_pct", "凌犯佔比 {pct}%").format(pct=pct))
            if m["relation_type"] == "ankai" and m["score"] < 45:
                reasons.append(caution_reasons_i18n.get("ankai_low", "安壊低分"))
            if m["score"] < 45:
                reasons.append(caution_reasons_i18n.get("score_low", "分數偏低（{score}）").format(score=m['score']))
            if reasons:
                caution_months.append({
                    "month": m["month"],
                    "score": m["score"],
                    "reasons": reasons,
                    "description": self._caution_month_description(m, reasons, strat_i18n)
                })
        return caution_months

    def _find_consecutive_groups(self, month_nums: list) -> list:
        """找出連續月份群組"""
        if not month_nums:
            return []
        groups = []
        group = [month_nums[0]]
        for i in range(1, len(month_nums)):
            if month_nums[i] == month_nums[i - 1] + 1:
                group.append(month_nums[i])
            else:
                if len(group) >= 2:
                    groups.append(group)
                group = [month_nums[i]]
        if len(group) >= 2:
            groups.append(group)
        return groups

    def _build_ryouhan_outlook(self, monthly_trend: list, strat_i18n: dict) -> dict:
        """全年凌犯概覽"""
        ryouhan_month_nums = [m["month"] for m in monthly_trend if m["ryouhan_ratio"] > 0]
        total_ratio = sum(m["ryouhan_ratio"] for m in monthly_trend) / 12
        consecutive_groups = self._find_consecutive_groups(ryouhan_month_nums)
        return {
            "affected_months": ryouhan_month_nums,
            "total_ratio": round(total_ratio, 2),
            "consecutive_groups": consecutive_groups,
            "description": self._ryouhan_outlook_description(ryouhan_month_nums, consecutive_groups, total_ratio, strat_i18n)
        }

    def _analyze_yearly_rhythm(self, monthly_trend: list, strat_i18n: dict) -> dict:
        """分析年度節奏型態（前重/後重/V型/穩定）"""
        first_half = [m["score"] for m in monthly_trend if m["month"] <= 6]
        second_half = [m["score"] for m in monthly_trend if m["month"] > 6]
        avg_first = sum(first_half) / len(first_half) if first_half else 60
        avg_second = sum(second_half) / len(second_half) if second_half else 60

        scores = [m["score"] for m in monthly_trend]
        min_idx = scores.index(min(scores))
        max_idx = scores.index(max(scores))

        diff = avg_first - avg_second
        if diff >= 10:
            rhythm_type = "front_heavy"
        elif diff <= -10:
            rhythm_type = "back_heavy"
        elif min_idx in range(3, 9) and avg_first > min(scores) + 10 and avg_second > min(scores) + 10:
            rhythm_type = "v_shape"
        elif max_idx in range(3, 9) and avg_first < max(scores) - 10 and avg_second < max(scores) - 10:
            rhythm_type = "inv_v_shape"
        else:
            rhythm_type = "stable"

        rhythm_i18n = strat_i18n.get("yearly_rhythm", {})
        rhythm_tpl = rhythm_i18n.get(rhythm_type, "")
        if rhythm_type == "v_shape":
            rhythm_desc = rhythm_tpl.format(month=min_idx + 1) if rhythm_tpl else ""
        elif rhythm_type == "inv_v_shape":
            rhythm_desc = rhythm_tpl.format(month=max_idx + 1) if rhythm_tpl else ""
        else:
            rhythm_desc = rhythm_tpl

        return {
            "type": rhythm_type,
            "first_half_avg": round(avg_first),
            "second_half_avg": round(avg_second),
            "description": rhythm_desc
        }

    def _safe_haven_description(self, start: int, end: int, cluster_type: str | None, strat_i18n: dict = None) -> str:
        """避風港區段的描述文字"""
        period = f"{start}-{end}月"
        sh = (strat_i18n or {}).get("safe_haven", {})
        if cluster_type == "eishin_cluster":
            tpl = sh.get("eishin_cluster", "{tag}{period}連續栄親高分，這段期間是全年最穩固的避風港，適合推進重要事項。")
            return tpl.format(tag=RELATION_TAG['eishin'], period=period)
        elif cluster_type == "gyotai_cluster":
            tpl = sh.get("gyotai_cluster", "{tag}{period}連續業胎月，前世因緣深厚的時期，人際合作和共同事業特別順利。")
            return tpl.format(tag=RELATION_TAG['gyotai'], period=period)
        tpl = sh.get("default", "{tag}{period}連續高分段，運勢穩定向好，適合積極行動和做出重要決定。")
        return tpl.format(tag=DARK_WEEK_TAG, period=period)

    def _best_month_description(self, m: dict, strat_i18n: dict = None) -> str:
        """最佳月份的建議文字"""
        rel = m["relation_type"]
        score = m["score"]
        month = m["month"]
        bm = (strat_i18n or {}).get("best_month", {})

        if rel == "eishin":
            tpl = bm.get("eishin", "{tag}{month}月栄親月（{score}分），全年最佳行動期之一，大膽推進計畫。")
            return tpl.format(tag=RELATION_TAG['eishin'], month=month, score=score)
        elif rel == "gyotai":
            tpl = bm.get("gyotai", "{tag}{month}月業胎月（{score}分），適合合作、簽約、建立夥伴關係。")
            return tpl.format(tag=RELATION_TAG['gyotai'], month=month, score=score)
        elif rel == "mei":
            tpl = bm.get("mei", "{tag}{month}月命月（{score}分），本命能量強化，適合開創性的行動。")
            return tpl.format(tag=RELATION_TAG['mei'], month=month, score=score)
        elif score >= 75:
            tpl = bm.get("high_score", "{tag}{month}月高分（{score}分），運勢良好，把握機會積極行動。")
            return tpl.format(tag=RELATION_TAG.get(rel, DARK_WEEK_TAG), month=month, score=score)
        tpl = bm.get("default", "{tag}{month}月（{score}分），相對穩定的時期，可安排重要事務。")
        return tpl.format(tag=RELATION_TAG.get(rel, DARK_WEEK_TAG), month=month, score=score)

    def _caution_month_description(self, m: dict, reasons: list, strat_i18n: dict = None) -> str:
        """警戒月的描述文字"""
        month = m["month"]
        cm = (strat_i18n or {}).get("caution_month", {})
        if m["ryouhan_ratio"] >= 0.5:
            tpl = cm.get("ryouhan", "{tag}{month}月凌犯嚴重，吉凶逆轉機率高，避免重大決策和簽約。守勢為主，等待時機。")
            return tpl.format(tag=RYOUHAN_TAG, month=month)
        elif m["relation_type"] == "ankai":
            tpl = cm.get("ankai", "{tag}{month}月安壊月，關係容易破裂，避免衝突和冒險，低調行事。")
            return tpl.format(tag=RELATION_TAG['ankai'], month=month)
        tpl = cm.get("default", "{tag}{month}月運勢偏低（{score}分），保守行事，不宜冒進。")
        return tpl.format(tag=RELATION_TAG.get(m['relation_type'], DARK_WEEK_TAG), month=month, score=m['score'])

    def _ryouhan_outlook_description(self, months: list, groups: list, ratio: float, strat_i18n: dict = None) -> str:
        """全年凌犯概覽描述"""
        ro = (strat_i18n or {}).get("ryouhan_outlook", {})
        if not months:
            return ro.get("no_ryouhan", "今年沒有凌犯月份，全年運勢走向清晰可預測。")

        parts = []
        consec_tpl = ro.get("consecutive_format", "{start}-{end}月連續{count}個月凌犯")
        scatter_tpl = ro.get("scattered_format", "{months}月零星凌犯")
        if groups:
            for g in groups:
                parts.append(consec_tpl.format(start=g[0], end=g[-1], count=len(g)))
        scattered = [m for m in months if not any(m in g for g in groups)]
        if scattered:
            parts.append(scatter_tpl.format(months=', '.join(str(m) for m in scattered)))

        advice = ""
        if ratio >= 0.3:
            advice = ro.get("high_ratio", "凌犯佔比偏高，今年整體需謹慎行事，重要決策盡量安排在非凌犯月。")
        elif groups:
            longest = max(groups, key=len)
            has_consec = ro.get("has_consecutive", "留意{start}-{end}月連續凌犯期，這段期間盡量避開重大行動。")
            advice = has_consec.format(start=longest[0], end=longest[-1])
        else:
            advice = ro.get("low_impact", "凌犯零星分布，影響有限，留意個別月份即可。")

        return f"{RYOUHAN_TAG}" + "。".join(parts) + "。" + advice

    def _generate_dynamic_tip(self, m: dict, strat_i18n: dict = None) -> str:
        """根據月份數據動態生成月度提示"""
        score = m["score"]
        rel = m["relation_type"]
        ryouhan = m["ryouhan_ratio"]
        dt = (strat_i18n or {}).get("dynamic_tips", {})

        # 高分 + 栄親
        if score >= 80 and rel == "eishin":
            return dt.get("eishin_high", "{tag}高分月，放手去做想做的事，成功率高。").format(tag=RELATION_TAG['eishin'])
        # 高分 + 業胎
        if score >= 80 and rel == "gyotai":
            return dt.get("gyotai_high", "{tag}高分月，人際合作會帶來好結果，主動出擊。").format(tag=RELATION_TAG['gyotai'])
        # 高分 + 凌犯
        if score >= 70 and ryouhan > 0.3:
            return dt.get("high_ryouhan", "{tag}，分數不錯但有凌犯干擾，好事多磨，耐心處理意外狀況。").format(tag=RYOUHAN_TAG)
        # 高分一般
        if score >= 75:
            return dt.get("high_general", "{tag}運勢穩定偏高，適合推進計畫和做決定。").format(tag=RELATION_TAG.get(rel, DARK_WEEK_TAG))
        # 中等 + 無凌犯
        if 60 <= score < 75 and ryouhan == 0:
            return dt.get("mid_clean", "{tag}中等穩定，按部就班推進，不急不緩。").format(tag=RELATION_TAG.get(rel, DARK_WEEK_TAG))
        # 中等 + 凌犯
        if 60 <= score < 75 and ryouhan > 0:
            return dt.get("mid_ryouhan", "{tag}，運勢中等偏有凌犯波動，遇到反覆屬正常，穩住心態。").format(tag=RYOUHAN_TAG)
        # 低分 + 重凌犯
        if score < 50 and ryouhan >= 0.5:
            return dt.get("low_heavy_ryouhan", "{tag}嚴重，守勢為主，避免冒險和重大決策。").format(tag=RYOUHAN_TAG)
        # 低分 + 安壊
        if score < 50 and rel == "ankai":
            return dt.get("low_ankai", "{tag}低分月，人際關係容易緊張，低調行事、遠離是非。").format(tag=RELATION_TAG['ankai'])
        # 低分一般
        if score < 50:
            return dt.get("low_general", "{tag}運勢偏低，養精蓄銳，為下個高峰期做準備。").format(tag=RELATION_TAG.get(rel, DARK_WEEK_TAG))
        # 中偏低
        return dt.get("default", "{tag}運勢平穩，做好手邊的事，不需要太大動作。").format(tag=RELATION_TAG.get(rel, DARK_WEEK_TAG))

    def _generate_monthly_strategy(self, _weekly_data: list, all_daily: list, ryouhan_count: int, days_in_month: int) -> dict:
        """
        月度趨吉避凶策略分析

        基於每日運勢資料生成 best_days、avoid_days、action_windows。

        Args:
            _weekly_data: 週次資料列表（保留供未來使用）
            all_daily: 每日概覽資料列表
            ryouhan_count: 凌犯天數
            days_in_month: 該月天數

        Returns:
            月度策略 dict
        """
        # === 1. best_days：top 3 高分日（score >= 70，無凌犯/羅刹/命/胎/業/壊） ===
        # 注意：不再整體排除 is_dark_week，原典各日吉凶不同
        # 但命/胎/業/壊日即使高分也不應推薦（原典禁忌）
        _excluded_day_types = ("命の日", "胎の日", "業の日", "壊の日")
        clean_high = [d for d in all_daily
                      if d["score"] >= 70
                      and not d.get("ryouhan_active", False)
                      and not (d.get("special_day") and "羅刹" in (d.get("special_day") or ""))
                      and d.get("sanki_day_type", "") not in _excluded_day_types]
        clean_high.sort(key=lambda x: -x["score"])
        best_days = []
        for d in clean_high[:3]:
            best_days.append({
                "date": d["date"],
                "weekday": d["weekday"],
                "score": d["score"],
                "reason": self._best_day_reason(d)
            })

        # === 2. avoid_days：安壊+凌犯、暗黒+羅刹等危險組合 ===
        avoid_days = []
        for d in all_daily:
            dangers = []
            if d.get("ryouhan_active") and d.get("is_dark_week"):
                dangers.append("凌犯+暗黒の一週間")
            elif d.get("ryouhan_active") and d.get("special_day") and "羅刹" in (d.get("special_day") or ""):
                dangers.append("凌犯+羅刹日")
            elif d.get("is_dark_week") and d.get("special_day") and "羅刹" in (d.get("special_day") or ""):
                dangers.append("暗黒+羅刹日")
            elif d["score"] < 40 and d.get("ryouhan_active"):
                dangers.append("凌犯低分")

            if dangers:
                avoid_days.append({
                    "date": d["date"],
                    "weekday": d["weekday"],
                    "score": d["score"],
                    "reasons": dangers
                })

        # === 3. action_windows：連續 3+ 天 score >= 60 的最佳行動區間 ===
        action_windows = []
        window_start = None
        window_days = []
        for d in all_daily:
            if d["score"] >= 60 and not d.get("ryouhan_active", False):
                if window_start is None:
                    window_start = d["date"]
                window_days.append(d)
            else:
                if window_start is not None and len(window_days) >= 3:
                    avg = round(sum(x["score"] for x in window_days) / len(window_days))
                    action_windows.append({
                        "start_date": window_start,
                        "end_date": window_days[-1]["date"],
                        "days": len(window_days),
                        "avg_score": avg,
                        "description": f"連續 {len(window_days)} 天穩定期（均分 {avg}），適合安排重要事務（依{SANKI_TAG}推算）。"
                    })
                window_start = None
                window_days = []
        # 收尾
        if window_start is not None and len(window_days) >= 3:
            avg = round(sum(x["score"] for x in window_days) / len(window_days))
            action_windows.append({
                "start_date": window_start,
                "end_date": window_days[-1]["date"],
                "days": len(window_days),
                "avg_score": avg,
                "description": f"連續 {len(window_days)} 天穩定期（均分 {avg}），適合安排重要事務（依{SANKI_TAG}推算）。"
            })

        return {
            "best_days": best_days,
            "avoid_days": avoid_days,
            "action_windows": action_windows
        }

    def _best_day_reason(self, d: dict) -> str:
        """最佳日的理由文字"""
        parts = [f"運勢 {d['score']} 分"]
        if d.get("special_day"):
            if "甘露" in d["special_day"]:
                parts.append("甘露日加持（T21 p.398b）")
            elif "金剛" in d["special_day"]:
                parts.append("金剛峯日加持（T21 p.398b-c）")
        return "，".join(parts)

    def calculate_yearly_fortune_range(self, birth_date: date, start_year: int, end_year: int, lang: str = 'zh-TW') -> list:
        """
        批次計算多年運勢（九曜流年法）

        復用既有 calculate_yearly_fortune，逐年計算後彙整。

        Args:
            birth_date: 出生日期
            start_year: 起始年份
            end_year: 結束年份（含）

        Returns:
            多年運勢資料列表
        """
        results = []
        for year in range(start_year, end_year + 1):
            results.append(self.calculate_yearly_fortune(birth_date, year, lang=lang))
        return results

    # ==================== 通用吉日查詢 ====================

    # 吉日查詢類別定義
    # 關係類型對照：mei(命), gyotai(業胎), eishin(栄親), yusui(友衰), ankai(安壊), kisei(危成)
    # 吉日分類設定
    # 注意：favor_relations 指宿曜關係類型（非三九日型）。gyotai/mei 雖然在三九法中
    # 業日「所作不成就」、命/胎日「不宜舉動百事」(T21 p.397c)，但 _evaluate_day_quality
    # 會排除這些日型，所以 favor_relations 只影響 relation_type 篩選，不會推薦到凶日。
    # favor_weekdays 除 teihatsu 外均為系統設計，非 T21n1299 原典記載。
    LUCKY_DAY_CATEGORIES = {
        "career": {
            "name": "事業",
            "icon": "briefcase",
            "actions": {
                "interview": {"name": "求職面試", "favor_relations": ["eishin", "gyotai"], "favor_score": 75},
                "resign": {"name": "離職提出", "favor_relations": ["yusui"], "month_day_range": [1, 5, 25, 31], "favor_score": 65},
                "opening": {"name": "開業", "favor_relations": ["eishin", "mei"], "favor_score": 80},
                "contract": {"name": "簽約", "favor_relations": ["eishin", "gyotai"], "favor_score": 70}
            }
        },
        "study": {
            "name": "學業",
            "icon": "book",
            "actions": {
                "enrollment": {"name": "入學報到", "favor_relations": ["eishin", "gyotai"], "favor_score": 70},
                "exam": {"name": "考試", "favor_relations": ["eishin", "mei"], "favor_weekdays": [1, 3], "favor_score": 75},
                "tutor": {"name": "補習報名", "favor_relations": ["gyotai", "yusui"], "favor_score": 65}
            }
        },
        "housing": {
            "name": "居住",
            "icon": "house",
            "actions": {
                "move_in": {"name": "搬家入宅", "favor_relations": ["eishin", "mei"], "favor_score": 75},
                "renovation": {"name": "裝潢開工", "favor_relations": ["eishin"], "favor_weekdays": [0, 3], "favor_score": 70},
                "purchase": {"name": "購屋簽約", "favor_relations": ["eishin", "gyotai"], "favor_score": 80}
            }
        },
        "marriage": {
            "name": "婚姻",
            "icon": "heart",
            "actions": {
                "register": {"name": "結婚登記", "favor_relations": ["eishin", "mei", "gyotai", "yusui"], "favor_score": 70},
                "wedding": {"name": "婚禮", "favor_relations": ["eishin", "gyotai", "mei", "yusui"], "favor_score": 70},
                "engagement": {"name": "訂婚", "favor_relations": ["eishin", "gyotai", "yusui"], "favor_score": 70}
            }
        },
        "medical": {
            "name": "醫療",
            "icon": "heart-pulse",
            "actions": {
                "surgery": {"name": "手術", "favor_relations": ["eishin"], "avoid_relations": ["ankai", "kisei"], "favor_score": 80},
                "checkup": {"name": "健康檢查", "favor_relations": ["yusui", "eishin"], "favor_score": 65},
                "visit": {"name": "看診", "favor_relations": ["yusui"], "favor_score": 60}
            }
        },
        "travel": {
            "name": "旅行",
            "icon": "airplane",
            "actions": {
                "abroad": {"name": "出國", "favor_relations": ["eishin", "gyotai"], "favor_score": 75},
                "trip": {"name": "旅遊出發", "favor_relations": ["eishin", "yusui"], "favor_score": 70}
            }
        },
        "grooming": {
            "name": "剃髮",
            "icon": "brightness-high",
            "actions": {
                "teihatsu": {
                    "name": "剃髮",
                    "favor_relations": ["eishin", "mei", "gyotai"],
                    "avoid_relations": ["ankai"],
                    # 水曜(清淨)/金曜(莊嚴)吉、火曜忌 — 日本宿曜道實踐傳承，非 T21 原典
                    "favor_weekdays": [2, 4],
                    "avoid_weekdays": [1],
                    "avoid_birth_mansion": True,  # T21 p.397c「命宿日不宜舉動百事」
                    # 女宿(8)理髮吉、鬼宿(21)萬事大吉 — 日本宿曜道實踐傳承
                    # 室宿(11)理髮吉 — 日本宿曜道實踐傳承（mansions.json 記載佛事/祈願吉）
                    "favor_mansions": [11, 8, 21],
                    "favor_score": 70
                }
            }
        },
        "beauty": {
            "name": "美容造型",
            "icon": "scissors",
            "actions": {
                "hair_coloring": {"name": "染髮", "favor_relations": ["eishin"], "favor_score": 65},
                "perm": {"name": "燙髮", "favor_relations": ["eishin", "gyotai"], "favor_score": 65},
                "nail": {"name": "美甲", "favor_relations": ["eishin", "yusui"], "favor_score": 60},
                "skincare": {"name": "護膚美容", "favor_relations": ["eishin", "mei"], "favor_score": 65},
                "tattoo": {"name": "紋繡/刺青", "favor_relations": ["eishin"], "avoid_relations": ["ankai"], "favor_score": 70}
            }
        },
        "dating": {
            "name": "感情",
            "icon": "chat-heart",
            "actions": {
                "first_date": {"name": "第一次約會", "favor_relations": ["eishin", "gyotai", "yusui"], "favor_weekdays": [4, 5], "favor_score": 70},
                "confession": {"name": "告白", "favor_relations": ["eishin", "mei", "yusui"], "favor_score": 70},
                "matchmaking": {"name": "相親", "favor_relations": ["eishin", "gyotai", "yusui"], "favor_score": 70},
                "breakup": {"name": "分手", "favor_relations": ["yusui", "ankai"], "avoid_relations": ["kisei"], "favor_score": 60}
            }
        },
        "shopping": {
            "name": "購物",
            "icon": "bag",
            "actions": {
                "clothing": {"name": "買衣服", "favor_relations": ["eishin", "yusui"], "favor_weekdays": [4, 5, 6], "favor_score": 65},
                "jewelry": {"name": "買首飾", "favor_relations": ["eishin", "mei"], "favor_score": 70},
                "big_purchase": {"name": "大額消費", "favor_relations": ["eishin", "gyotai"], "favor_score": 75}
            }
        }
    }

    def get_lucky_days(
        self,
        birth_date: date,
        category: str,
        action: str,
        days_ahead: int = 30
    ) -> dict:
        """
        通用吉日查詢

        Args:
            birth_date: 西曆生日
            category: 類別（career/study/housing/marriage/medical/travel/beauty/dating/shopping）
            action: 具體項目
            days_ahead: 查詢未來幾天（預設 30）

        Returns:
            吉日列表和建議
        """
        from datetime import timedelta

        # 驗證類別和項目
        if category not in self.LUCKY_DAY_CATEGORIES:
            raise ValueError(f"無效的類別: {category}")

        cat_config = self.LUCKY_DAY_CATEGORIES[category]
        if action not in cat_config["actions"]:
            raise ValueError(f"無效的項目: {action}")

        action_config = cat_config["actions"][action]

        mansion = self.get_mansion(birth_date)
        user_element = mansion["element"]
        user_index = mansion["index"]

        today = date.today()
        lucky_days = []
        avoid_days = []

        fortune_data = self._load_fortune_data()

        # 取得項目配置
        favor_relations = action_config.get("favor_relations", ["eishin"])
        avoid_relations = action_config.get("avoid_relations", ["ankai", "kisei"])
        favor_score = action_config.get("favor_score", 70)
        favor_weekdays = action_config.get("favor_weekdays", None)
        favor_mansions = action_config.get("favor_mansions", None)
        month_day_range = action_config.get("month_day_range", None)

        # 吉宿名稱對照（用於顯示）
        mansion_names = {11: "室宿", 8: "女宿", 21: "鬼宿"}

        for i in range(days_ahead):
            check_date = today + timedelta(days=i)

            # 計算當日運勢（含等級）
            daily_fortune = self.calculate_daily_fortune(birth_date, check_date)
            score = daily_fortune["fortune"]["overall"]
            day_level = daily_fortune["fortune"].get("level", "chukichi")

            # 取得當日資訊
            weekday = check_date.weekday()
            jp_weekday = (weekday + 1) % 7
            day_element = fortune_data["weekday_elements"][str(jp_weekday)]["element"]
            day_name = fortune_data["weekday_elements"][str(jp_weekday)]["name"]

            # 計算當日宿（修正後宿位）
            day_mansion_index = self._get_corrected_mansion_index(check_date)

            # 計算與本命宿的關係
            relation = self.get_relation_type(user_index, day_mansion_index)
            relation_type = relation["type"]

            # 判斷是否吉日
            is_lucky = False
            lucky_reason = ""

            # 統一品質評估（凌犯/壊の日/羅刹日/暗黒の一週間/甘露日/金剛峯日等）
            quality = self._evaluate_day_quality(daily_fortune, action)
            if quality["excluded"]:
                if len(avoid_days) < 5:
                    avoid_days.append({
                        "date": check_date.isoformat(),
                        "weekday": day_name,
                        "score": score,
                        "level": day_level,
                        "reason": quality["exclude_reason"]
                    })
                continue

            # 檢查避開的關係
            if relation_type in avoid_relations:
                if len(avoid_days) < 5:
                    avoid_days.append({
                        "date": check_date.isoformat(),
                        "weekday": day_name,
                        "score": score,
                        "level": day_level,
                        "reason": f"{relation['name']}日，不宜{action_config['name']}"
                    })
                continue

            # 檢查避開的星期（如火曜日忌剃髮）
            avoid_weekdays = action_config.get("avoid_weekdays", None)
            if avoid_weekdays and weekday in avoid_weekdays:
                if len(avoid_days) < 5:
                    avoid_days.append({
                        "date": check_date.isoformat(),
                        "weekday": day_name,
                        "score": score,
                        "level": day_level,
                        "reason": f"{day_name}不宜{action_config['name']}"
                    })
                continue

            # 檢查本命宿日（剃髮忌本命宿日）
            if action_config.get("avoid_birth_mansion") and day_mansion_index == user_index:
                if len(avoid_days) < 5:
                    avoid_days.append({
                        "date": check_date.isoformat(),
                        "weekday": day_name,
                        "score": score,
                        "level": day_level,
                        "reason": "本命宿日，不宜剃髮"
                    })
                continue

            # 檢查等級過低（小凶/凶 = 避開）
            if day_level in ("shokyo", "kyo"):
                if len(avoid_days) < 5:
                    avoid_days.append({
                        "date": check_date.isoformat(),
                        "weekday": day_name,
                        "score": score,
                        "level": day_level,
                        "reason": f"運勢{self.LEVEL_NAMES[day_level]['zh']}，建議避開"
                    })
                continue

            # 檢查特定月日範圍（如離職適合月初月底）
            if month_day_range:
                day_of_month = check_date.day
                in_range = any(
                    day_of_month <= month_day_range[1] or day_of_month >= month_day_range[2]
                    for _ in [1]
                )
                if not in_range:
                    continue

            # 判斷吉日條件
            if relation_type in favor_relations:
                is_lucky = True
                lucky_reason = f"{relation['name']}日，{self._get_relation_benefit(relation_type, action)}"
            elif favor_mansions and day_mansion_index in favor_mansions:
                is_lucky = True
                m_name = mansion_names.get(day_mansion_index, f"index {day_mansion_index}")
                lucky_reason = f"當日宿為{m_name}，傳統上特別適合{action_config['name']}。{m_name}之日淨身修儀，事半功倍"
            elif day_element == user_element and score >= favor_score:
                is_lucky = True
                lucky_reason = f"{day_name}（{day_element}曜）與你的本命元素相同，能量共振特別強烈。這天你的狀態比平時穩定，做需要專注和耐心的事情效率最高"
            elif self._is_generating(day_element, user_element) and score >= favor_score:
                is_lucky = True
                lucky_reason = f"{day_name}的{day_element}曜能量正在滋養你的本命元素，形成相生的良性循環。這天你會感覺做事順手，外在環境彷彿在配合你的節奏"
            elif score >= favor_score + 5:
                # 特定星期加分
                if favor_weekdays and weekday in favor_weekdays:
                    is_lucky = True
                    lucky_reason = f"整體運勢{score}分，加上{day_name}本身就適合{action_config['name']}，天時地利兼具"
                elif score >= favor_score + 10:
                    is_lucky = True
                    lucky_reason = f"整體運勢高達{score}分，各方面能量都處於高峰期，適合處理重要事務"

            if is_lucky and len(lucky_days) < 8:
                # 評級直接取等級名稱，再根據品質評估調整
                rating = self.LEVEL_NAMES.get(day_level, {"zh": "中吉"})["zh"]
                if quality["rating_shift"] != 0:
                    rating = self._shift_rating_name(rating, quality["rating_shift"])

                # 時段建議
                time_tip = self._get_personal_time_tip(day_element, user_element, action)

                day_entry: dict = {
                    "date": check_date.isoformat(),
                    "weekday": day_name,
                    "score": score,
                    "level": day_level,
                    "rating": rating,
                    "reason": lucky_reason,
                    "best_time": time_tip["best_time"],
                    "avoid_time": time_tip["avoid_time"]
                }
                if quality["conflicts"]:
                    day_entry["conflicts"] = quality["conflicts"]
                if quality["boosts"]:
                    day_entry["boosts"] = quality["boosts"]

                lucky_days.append(day_entry)

        return {
            "category": category,
            "category_name": cat_config["name"],
            "action": action,
            "action_name": action_config["name"],
            "your_mansion": {
                "name_jp": mansion["name_jp"],
                "reading": mansion["reading"],
                "element": user_element
            },
            "lucky_days": lucky_days,
            "avoid_days": avoid_days,
            "advice": self._get_action_advice(category, action, user_element)
        }

    # 吉日理由：按類別 + 關係類型提供差異化的好處描述
    LUCKY_DAY_BENEFITS = {
        "career": {
            "eishin": "貴人運極強，面試官、主管、合作方都對你有好印象。今天做出的職場決策成功率特別高，簽約、談判、提案都適合排在這天",
            "gyotai": "直覺特別準，能敏銳地判斷出哪個選擇對你的職涯最有利。如果有兩個 offer 在猶豫，今天的第一反應通常是對的",
            "mei": "你的存在感和說服力在今天達到高峰。面試展現的自信、開業的儀式感、簽約時的氣場，都會讓對方留下深刻印象",
            "yusui": "能量平穩順暢，適合處理需要冷靜判斷的事務。今天做的決定比較理性、不容易受情緒影響，是簽約和談合作的好時機"
        },
        "study": {
            "eishin": "學習運極佳。今天遇到的老師或同學可能成為長期的學習夥伴，報名的課程或考試也容易取得好結果",
            "gyotai": "理解力和記憶力處於高峰。考試時平時想不起來的知識今天會自然浮現，入學或報名的選擇也會是對的方向",
            "mei": "表達力強，適合口試或需要上台的考試。你的思路清晰、回答有條理，考官容易被你的自信吸引",
            "yusui": "心態穩定不緊張，適合需要持久專注力的考試。不會因為粗心或焦慮而失常，正常發揮就能拿到好成績"
        },
        "housing": {
            "eishin": "搬家和入宅的能量場極佳。新環境的氣場和你高度契合，住進去之後的生活品質會比預期好。購屋簽約也容易談到理想條件",
            "gyotai": "對房屋的直覺特別準。看房子的時候你能感受到哪些地方「對」、哪些地方「不對」。跟著感覺走，選到的房子通常不會讓你後悔",
            "mei": "你的氣場和新空間容易產生共鳴。搬家入宅之後，你會很快適應新環境。裝潢開工也容易順利推進",
            "yusui": "穩定的能量適合需要冷靜判斷的購屋決策。不容易被銷售話術影響，能夠理性分析條件再做決定"
        },
        "marriage": {
            "eishin": "婚姻能量最佳日。兩人的默契會被放大，登記或婚禮都充滿祝福的氛圍。這天互相許下的承諾特別有重量",
            "gyotai": "感情的直覺力在今天最強。訂婚或登記時你會確認「對，就是這個人」的感覺。緣分的共鳴在這天特別明顯",
            "mei": "今天的你散發著幸福的光環。婚禮的氛圍會特別好，到場的賓客也能感受到你們的喜悅。適合拍婚紗或舉辦儀式",
            "yusui": "穩定和諧的日子，適合想要安靜溫馨的登記或訂婚。沒有戲劇化的起伏，但充滿踏實的幸福感"
        },
        "medical": {
            "eishin": "醫療運佳。今天遇到的醫生比較能準確判斷你的狀況，手術和治療的順利度也比較高。醫病溝通特別順暢",
            "gyotai": "身體的自癒力今天比較強。健康檢查的結果也比較能如實反映你的狀況，不容易有假陽性或假陰性干擾判斷",
            "mei": "你能比平時更清楚地描述自己的症狀。醫生因此更容易做出準確的診斷。看診的效率和品質都比較好",
            "yusui": "心態平穩不焦慮，適合做需要放鬆心情的檢查項目。手術前的心理狀態也比較好，有助於術後恢復"
        },
        "travel": {
            "eishin": "旅行運極佳。出發時的能量順暢，旅途中容易遇到好的人和好的事。安排在這天出發的旅程，體驗通常超出預期",
            "gyotai": "旅行中的直覺特別準。選餐廳、選景點、選路線都容易踩到好的。不需要做太多攻略，隨性走反而能發現驚喜",
            "mei": "適合一個人或少數好友的深度旅行。你的感受力在今天特別敏銳，能從旅行中獲得比平時更多的感悟",
            "yusui": "旅途平順、不容易遇到延誤或意外。適合需要穩定行程的出差旅行，或者帶長輩出遊"
        },
        "grooming": {
            "eishin": "淨身修儀的最佳時機。剃髮時心念清明，身心調和。宿曜栄親之力加持，當日行法功德倍增",
            "gyotai": "業胎之日的淨身，能深化自身與宿曜的連結。剃髮後身輕意淨，直覺敏銳，適合接續行法或誦經",
            "mei": "本命宿能量最強之日。身儀端正本身即是修行的體現，今天的剃髮能強化本命宿的守護力",
            "yusui": "穩定安寧之日，適合從容淨身。不急不躁地完成剃髮，保持平常心即是最好的狀態"
        },
        "beauty": {
            "eishin": "美容運極佳。今天去做造型的效果特別好，設計師能準確抓到你想要的感覺。染髮、護膚的成品都會讓你滿意",
            "gyotai": "你對自己適合什麼造型的直覺今天特別準。如果一直在猶豫要不要嘗試新風格，今天是最好的時機",
            "mei": "今天做出的造型改變最能展現你的個人特色。適合做比較大幅度的形象改造，效果會比你想像中自然",
            "yusui": "穩定的日子，適合做維護型的美容。染髮補色、定期護膚、修剪整理，今天做的效果持久穩定"
        },
        "dating": {
            "eishin": "桃花運最旺的日子。約會的氣氛會比預期好，告白的成功率也高。你身上散發的魅力讓對方很難不被吸引",
            "gyotai": "你對對方的感覺今天特別準。第一次約會就能判斷出這個人適不適合深入交往。如果覺得對了，就大膽往前走",
            "mei": "你的吸引力在今天達到最大值。不管是相親還是約會，對方對你的第一印象都會非常好。自信地展現自己就好",
            "yusui": "適合不趕時間的深度約會。今天的節奏很舒服，兩個人可以慢慢聊、慢慢了解。不用刻意製造氣氛，自然就好"
        },
        "shopping": {
            "eishin": "購物運極佳。今天買到的東西滿意度高，特別是大額消費和首飾類。你的眼光比平時更準，不容易買到後悔的東西",
            "gyotai": "購物直覺很準。看到喜歡的東西不用猶豫太久，今天的第一反應通常是對的。適合買需要品味判斷的物品",
            "mei": "適合買能代表個人風格的物品。今天你對自己想要什麼特別清楚，不容易被行銷話術帶跑，買到的都是真心喜歡的",
            "yusui": "冷靜理性的購物日。不容易衝動消費，能在預算範圍內買到最划算的選擇。適合比價之後再下手的大額消費"
        }
    }

    def _get_relation_benefit(self, relation_type: str, action: str) -> str:
        """取得關係類型對特定行動的好處描述（按類別差異化）"""
        # 從 action 反查所屬的 category
        category = None
        for cat_key, cat_data in self.LUCKY_DAY_CATEGORIES.items():
            if action in cat_data["actions"]:
                category = cat_key
                break

        if category and category in self.LUCKY_DAY_BENEFITS:
            benefit = self.LUCKY_DAY_BENEFITS[category].get(relation_type)
            if benefit:
                return benefit

        # 通用 fallback
        fallback = {
            "eishin": "貴人運極強，周圍的人會自然而然地想幫你。這天做出的選擇成功率比平時高出許多",
            "gyotai": "直覺比平時更準。如果心裡對某件事有一個傾向，大膽跟著感覺走，結果通常不會讓你失望",
            "mei": "你的存在感和說服力在今天特別強。需要展現自己、爭取機會的事情排在這天最合適",
            "yusui": "能量平穩順暢，適合按部就班地推進計畫。這天做事效率穩定，不會有意外打亂節奏",
            "kisei": "需要比平時更謹慎，多花一點時間確認細節和備案",
            "ankai": "建議避開此日，能量場不利於重要決定"
        }
        return fallback.get(relation_type, "")

    def _get_action_advice(self, category: str, action: str, element: str) -> str:
        """取得特定行動的建議"""
        advice_templates = {
            "career": {
                "interview": f"{element}性本命宿者，面試時展現你最擅長的專業領域。準備好兩三個能具體量化成果的案例，比泛泛而談有效。上午時段精神狀態最佳，面試排在十點左右的效果最好。",
                "resign": f"{element}性本命宿者，離職時保持專業態度，把交接做好是對自己負責。選擇月初或月底提出，給雙方足夠的緩衝時間。不管離開的原因是什麼，好好道別比默默消失更有格局。",
                "opening": f"{element}性本命宿者，開業當天的氣場會影響初期的營運節奏。穿戴與本命元素相合的顏色出席、邀請你信任的朋友到場支持。開業前三個月專注在產品品質而非行銷曝光。",
                "contract": f"{element}性本命宿者，簽約前至少留兩天時間仔細審閱條款。不理解的地方不要不好意思問，模糊的條款事後容易產生爭議。選在你運勢高峰的時段簽署，心理狀態更從容。"
            },
            "study": {
                "enrollment": f"{element}性本命宿者，入學報到那天帶著好奇心去觀察新環境。主動跟同學打招呼、記住老師的名字，第一天的印象會影響整段學習經歷。",
                "exam": f"{element}性本命宿者，考試當天最重要的不是臨時抱佛腳，而是維持平常心。穿一件讓你覺得自信的衣服、提前到場熟悉環境、考前做三次深呼吸。你準備的比你以為的多。",
                "tutor": f"{element}性本命宿者，選補習班的時候先試聽再決定。老師的教學方式跟你的吸收習慣合不合比名氣重要，花一堂課的時間確認值不值得長期投入。"
            },
            "housing": {
                "move_in": f"{element}性本命宿者，搬家當天上午行動最順利。搬完之後在新家煮一壺水、開窗讓空氣流通，用你的生活痕跡取代空間原本的氣場。第一天晚上在新家好好吃一頓飯。",
                "renovation": f"{element}性本命宿者，裝潢開工前確認所有設計細節都已經溝通清楚。動工之後再改方案成本很高，不如前期多花一週確認。開工當天到場監工，展現你對品質的重視。",
                "purchase": f"{element}性本命宿者，購屋時理性分析比感性直覺重要。同一社區至少看三間再做決定，注意採光、通風、和周邊生活機能。房屋座向如果能跟本命元素相合是加分。"
            },
            "marriage": {
                "register": f"{element}性本命宿者，登記那天不用特別隆重，但要讓彼此感覺到這一刻的份量。帶一束花、一封手寫的信、或者一件有紀念意義的小禮物，多年後你們會慶幸留下了這些細節。",
                "wedding": f"{element}性本命宿者，婚禮當天你要做的只有一件事：享受這一天。其他的交給你信任的人去處理。提前跟主持人和攝影師溝通好節奏，確保你有足夠的時間跟重要的賓客說話。",
                "engagement": f"{element}性本命宿者，訂婚是兩個家庭的事，你的任務是讓雙方都感到被尊重。事前跟雙方父母分別溝通期待值，當天的流程盡量簡單明確。真誠比排場重要。"
            },
            "medical": {
                "surgery": f"{element}性本命宿者，手術前最重要的是充分了解流程和恢復計畫。把你的疑慮全部列出來跟醫生討論，不要帶著不安進手術室。準備好術後一到兩週的休養安排。",
                "checkup": f"{element}性本命宿者，健檢前一週維持正常生活即可，不用刻意調整飲食或作息。拿到報告後如果有紅字，不要自己上網查嚇自己，預約回診讓醫生解釋最準確。",
                "visit": f"{element}性本命宿者，看診前把症狀、發生時間、嚴重程度列成簡單的清單帶去。門診時間有限，條理清楚的描述能幫醫生更快做出判斷。有疑問就問，不要回家再後悔。"
            },
            "travel": {
                "abroad": f"{element}性本命宿者，出國前兩天把行李清單核對一次、把重要證件拍照備份在手機裡。到了當地先確認緊急聯絡方式和最近的醫療機構。準備做好了，剩下的就放心享受。",
                "trip": f"{element}性本命宿者，旅遊的精髓在於體驗而非打卡。不用把行程塞滿，留一些空白時間隨性探索。有時候迷路的那條小巷，反而藏著整趟旅行最美的風景。"
            },
            "grooming": {
                "teihatsu": f"{element}性本命宿者，剃髮前先沐浴淨身，以清晨或上午為佳。水曜日（水星之力，清淨智慧）和金曜日（金星之力，莊嚴身儀）是傳統上最適合剃髮的日子。火曜日災厄最重，務必避開。羅刹日不宜舉動百事，應避免。破壊の週中，原典記載栄日「剃髮吉」，其餘日型宜謹慎。剃髮後端坐片刻，收攝身心。"
            },
            "beauty": {
                "hair_coloring": f"{element}性本命宿者，染髮前一天不要洗頭，頭皮的天然油脂能保護髮質。選色的時候考慮你平時的穿著風格和膚色，百搭的色調比流行色更實用。",
                "perm": f"{element}性本命宿者，燙髮是比較大的造型改變，選擇跟你合作過的設計師最安心。提前一週把頭髮養好，避免在髮質受損的時候燙。",
                "nail": f"{element}性本命宿者，美甲選色搭配你本週的穿搭計畫會更實用。如果是第一次做凝膠甲，選有口碑的店家比選便宜的重要。",
                "skincare": f"{element}性本命宿者，做臉或護膚療程前一天避免去角質或使用刺激性保養品。療程後二十四小時內不要上妝、不要曬太陽。",
                "tattoo": f"{element}性本命宿者，紋繡或刺青是永久的改變，確認圖案和位置後至少等三天再決定。選擇衛生條件好、作品風格你喜歡的師傅。"
            },
            "dating": {
                "first_date": f"{element}性本命宿者，第一次約會地點選你熟悉的地方比較自在。不用刻意表演，做自己就好。對方如果值得深入了解，你的真實面貌比精心包裝更有吸引力。",
                "confession": f"{element}性本命宿者，告白不用準備長篇大論，把你的感受用最簡單的話說出來就好。選一個兩個人都放鬆的場合，不要在公共場所給對方壓力。",
                "matchmaking": f"{element}性本命宿者，相親時不要帶著「評估」的心態去看人。放輕鬆當作認識一個新朋友，聊天的品質比條件的比較更能看出一個人的本質。",
                "breakup": f"{element}性本命宿者，分手是一個需要勇氣的決定。做了就不要反覆，拖拖拉拉只會讓兩個人都更痛苦。好好說、面對面說、說清楚原因，是你對這段感情最後的尊重。"
            },
            "shopping": {
                "clothing": f"{element}性本命宿者，買衣服前先整理衣櫃，看看缺什麼再買什麼。帶一個審美品味好的朋友一起去，比自己猶豫半天有效率。",
                "jewelry": f"{element}性本命宿者，買首飾要試戴才知道適不適合。照片上好看的不一定適合你的膚色和體型，親自去店裡比較是最準的方法。",
                "big_purchase": f"{element}性本命宿者，大額消費前把預算上限寫下來，進店之後只看你預算範圍內的選項。不要被「加一點就能升級」的話術帶走，堅守底線是聰明消費的基本功。"
            }
        }
        return advice_templates.get(category, {}).get(action, "選擇運勢良好的日子進行，有助於事半功倍。")

    def _is_generating(self, elem1: str, elem2: str) -> bool:
        """檢查是否為相生關係（含日/月特殊元素）"""
        GENERATING_PAIRS = [
            ("木", "火"), ("火", "土"), ("土", "金"),
            ("金", "水"), ("水", "木"),
            ("日", "火"), ("月", "水")
        ]
        return (elem1, elem2) in GENERATING_PAIRS or (elem2, elem1) in GENERATING_PAIRS

    def _evaluate_day_quality(self, daily_fortune: dict, action_key: str | None = None) -> dict:
        """
        評估某天的品質（負面因素排除、正面因素加持）

        統一處理凌犯/壊の日/羅刹日/暗黒の一週間等排除條件，
        以及甘露日/金剛峯日/業の日/成の日等加持條件。

        Args:
            daily_fortune: calculate_daily_fortune 的回傳
            action_key: 具體行動（如 "denpo", "kanjo", "teihatsu"）

        Returns:
            品質評估結果
        """
        ryouhan = daily_fortune.get("ryouhan")
        sanki = daily_fortune.get("sanki", {})
        special_day = daily_fortune.get("special_day")
        day_type = sanki.get("day_type", "")

        excluded = False
        exclude_reason = ""
        rating_shift = 0
        shift_reasons: list[str] = []
        conflicts: list[str] = []
        boosts: list[str] = []

        # --- 排除條件 ---

        # 1. 凌犯期間
        if ryouhan:
            excluded = True
            exclude_reason = "凌犯期間，吉凶逆轉不穩定，不宜重要行動"
            conflicts.append("凌犯")

        # 2. 壊の日（原典：「宜作鎮壓、降伏怨讎及討伐阻壞奸惡之謀，餘並不堪」）
        #    降伏法/降伏護摩可行，一般吉日仍排除
        if day_type == "壊の日":
            if not excluded:
                excluded = True
                exclude_reason = "壊の日，降伏法可行，餘事不宜"
            conflicts.append("壊の日")

        # 3. 羅刹日（凌犯中逆轉為吉，但凌犯本身已排除）
        if special_day and special_day.get("type") == "rasetsu":
            if not ryouhan:
                if not excluded:
                    excluded = True
                    exclude_reason = "羅刹日，災厄之日，務必避開"
                conflicts.append("羅刹日")

        # 4. 破壊の週：不再整體排除，改為逐日判斷三九日型
        #    原典 T21n1299 p.397c-398a 各日吉凶：
        #    - 業日：「所作善惡亦不成就，甚衰」→ 已由起始日判斷排除
        #    - 栄日：「諸吉事並大吉」→ 不排除
        #    - 衰日：「唯宜解除諸惡、療病」→ 由降級條件處理
        #    - 安日：「移徙吉，遠行人入宅、造作園宅、安坐臥床帳、作壇場並吉」→ 不排除
        #    - 危日：「結交、婚姻、歡宴吉」→ 由降級條件處理
        #    - 成日：「修道學問、作諸成就法並吉」→ 不排除
        #    - 壊日：「宜作鎮壓、降伏」→ 已由壊日條件處理
        if sanki.get("is_dark_week", False):
            conflicts.append("破壊の週")
            # 剃髮特殊規則：暗黒の一週間中，栄日原典記載「出家人剃髮...吉」（p.397c-398a），
            # 故栄日不排除剃髮；其餘日型排除
            if action_key == "teihatsu" and not excluded:
                if day_type != "栄の日":
                    excluded = True
                    exclude_reason = "暗黒の一週間（非栄日），不宜剃髮"

        # --- 降級條件 ---

        # 5. 衰の日（原典：「唯宜解除諸惡、療病」T21 p.398a）
        #    「療病」對應現代 surgery/checkup/visit；「解除諸惡」偏除邪/破不吉
        if day_type == "衰の日":
            if action_key in ("surgery", "checkup", "visit"):
                # 衰日「療病」（T21 p.398a）→ 現代醫療行為（看診、手術、健檢）
                boosts.append("衰の日利療病")
            else:
                rating_shift -= 1
                shift_reasons.append("衰の日")
                conflicts.append("衰の日")

        # 6. 危の日（原典：「宜結交、定婚姻，歡宴聚會並吉」T21 p.397c-398a）
        #    但卷下另記「危壞日，並不宜遠行出、入移徙、買賣、婚姻...並凶」（T21 p.398a）
        #    兩處婚姻吉凶矛盾，社交聚會部分取「歡宴聚會吉」
        if day_type == "危の日":
            if action_key in (
                "gathering", "collaboration",  # 雙人吉日 PAIR_LUCKY_ACTIONS
                "first_date", "confession", "matchmaking",  # 個人吉日 LUCKY_DAY_CATEGORIES 社交類
                "register", "wedding", "engagement",  # 婚姻類（原典「定婚姻」吉）
            ):
                # 社交聚會/婚姻 原典明記吉（T21 p.397c-398a「宜結交、定婚姻，歡宴聚會並吉」）
                boosts.append("危の日利社交（歡宴聚會吉）")
            else:
                rating_shift -= 1
                shift_reasons.append("危の日")
                conflicts.append("危の日")

        # --- 加持條件 ---

        # 7. 甘露日
        if special_day and special_day.get("type") == "kanro":
            boosts.append("甘露日")
            if action_key in ("kanjo", "jukai"):
                rating_shift += 1
                shift_reasons.append("甘露日利灌頂/授戒")

        # 8. 金剛峯日
        if special_day and special_day.get("type") == "kongou":
            boosts.append("金剛峯日")

        # 8.5 栄の日（原典：「諸吉事並大吉」T21 p.397c）
        if day_type == "栄の日":
            boosts.append("栄の日")

        # 8.6 安の日（原典：「移徙吉...作壇場並吉」T21 p.397c）
        if day_type == "安の日":
            boosts.append("安の日")
            if action_key == "move_in":
                rating_shift += 1
                shift_reasons.append("安の日利搬遷（移徙吉）")

        # 8.7 友の日/親の日（原典：「宜結交朋友大吉」T21 p.391b）
        if day_type in ("友の日", "親の日"):
            boosts.append(day_type)

        # 9. 業の日（卷下 p.397c：「所作善惡亦不成就，甚衰」→ 排除）
        #    注：品三 p.391b 另記「所作皆吉祥」，兩處矛盾，系統從卷下
        if day_type == "業の日":
            if not excluded:
                excluded = True
                exclude_reason = "業の日，所作善惡亦不成就"
            conflicts.append("業の日")

        # 10. 命の日（原典：「不宜舉動百事」T21 p.391b / p.397c → 排除）
        if day_type == "命の日":
            if not excluded:
                excluded = True
                exclude_reason = "命の日，本命宿回歸，不宜舉動百事"
            conflicts.append("命の日")

        # 11. 胎の日（原典：「不宜舉動百事」T21 p.391b / p.397c → 排除）
        if day_type == "胎の日":
            if not excluded:
                excluded = True
                exclude_reason = "胎の日，三九第三期起始，不宜舉動百事"
            conflicts.append("胎の日")

        # 12. 成の日（原典：「宜修道學問、合和長年藥法，作諸成就法並吉」T21 p.398a）
        if day_type == "成の日":
            boosts.append("成の日")
            if action_key == "teaching":
                rating_shift += 1
                shift_reasons.append("成の日利教學（修道學問吉）")

        # 衝突判定：同時有實質衝突（非僅破壊の週標記）和加持 → 維持排除
        # 破壊の週只是資訊標記，逐日判斷由各日型條件處理
        real_conflicts = [c for c in conflicts if c != "破壊の週"]
        if boosts and real_conflicts and not excluded:
            excluded = True
            exclude_reason = f"{'、'.join(real_conflicts)}與{'、'.join(boosts)}衝突，宜避開"

        return {
            "excluded": excluded,
            "exclude_reason": exclude_reason,
            "rating_shift": rating_shift,
            "shift_reasons": shift_reasons,
            "conflicts": conflicts,
            "boosts": boosts,
        }

    @staticmethod
    def _shift_rating_name(rating_zh: str, shift: int) -> str:
        """在大吉/吉/中吉之間切換評級"""
        levels = ["中吉", "吉", "大吉"]
        try:
            idx = levels.index(rating_zh)
        except ValueError:
            return rating_zh
        new_idx = max(0, min(len(levels) - 1, idx + shift))
        return levels[new_idx]

    # ==================== 雙人吉日 ====================

    # 關係類型對應的吉日項目
    PAIR_LUCKY_ACTIONS = {
        "dating": {  # 交往對象
            "name": "交往對象",
            "actions": [
                {"key": "date", "name": "約會", "favor_relations": ["eishin", "gyotai", "yusui"], "favor_score": 70},
                {"key": "confession", "name": "告白", "favor_relations": ["eishin", "mei"], "favor_score": 75},
                {"key": "meet_parents", "name": "見家長", "favor_relations": ["eishin", "gyotai"], "favor_score": 80},
                {"key": "engagement", "name": "訂婚", "favor_relations": ["eishin", "gyotai"], "favor_score": 80},
                {"key": "register", "name": "結婚登記", "favor_relations": ["eishin", "mei", "gyotai"], "favor_score": 85},
                {"key": "wedding", "name": "婚禮", "favor_relations": ["eishin", "mei", "gyotai"], "favor_score": 85},
            ]
        },
        "spouse": {  # 配偶
            "name": "配偶",
            "actions": [
                {"key": "date", "name": "約會", "favor_relations": ["eishin", "gyotai", "yusui"], "favor_score": 65},
                {"key": "travel", "name": "旅遊", "favor_relations": ["eishin", "yusui"], "favor_score": 70},
                {"key": "discussion", "name": "重要商量", "favor_relations": ["eishin", "mei"], "favor_score": 75},
            ]
        },
        "parent": {  # 父母
            "name": "父母",
            "actions": [
                {"key": "visit", "name": "探親", "favor_relations": ["eishin", "yusui", "gyotai"], "favor_score": 65},
                {"key": "gift", "name": "送禮", "favor_relations": ["eishin", "yusui"], "favor_score": 60},
                {"key": "discussion", "name": "重要商談", "favor_relations": ["eishin", "mei"], "favor_score": 75},
            ]
        },
        "family": {  # 家人
            "name": "家人",
            "actions": [
                {"key": "gathering", "name": "聚會", "favor_relations": ["eishin", "yusui", "gyotai"], "favor_score": 65},
                {"key": "travel", "name": "旅遊", "favor_relations": ["eishin", "yusui"], "favor_score": 70},
                {"key": "gift", "name": "送禮", "favor_relations": ["eishin", "yusui"], "favor_score": 60},
            ]
        },
        "friend": {  # 朋友/同事
            "name": "朋友/同事",
            "actions": [
                {"key": "gathering", "name": "聚會", "favor_relations": ["eishin", "yusui", "gyotai"], "favor_score": 65},
                {"key": "collaboration", "name": "合作", "favor_relations": ["eishin", "gyotai"], "favor_score": 75},
                {"key": "travel", "name": "旅遊", "favor_relations": ["eishin", "yusui"], "favor_score": 70},
            ]
        },
        "master": {  # 師徒
            "name": "師徒",
            "actions": [
                {"key": "denpo", "name": "傳法", "favor_relations": ["eishin", "mei", "gyotai"], "favor_score": 80},
                {"key": "kanjo", "name": "灌頂", "favor_relations": ["eishin", "mei"], "favor_score": 80},
                {"key": "jukai", "name": "授戒", "favor_relations": ["eishin", "mei", "gyotai"], "favor_score": 80},
                {"key": "teaching", "name": "教學", "favor_relations": ["eishin", "gyotai", "yusui"], "favor_score": 70},
            ]
        }
    }

    def _get_personal_time_tip(self, day_element: str, user_element: str, action: str) -> dict:
        """根據七曜元素和本命元素生成個人吉日的時段建議"""

        ELEMENT_PEAK = {
            "日": "上午十點到十二點",
            "月": "下午六點到九點",
            "火": "下午兩點到四點",
            "水": "上午九點到十一點",
            "木": "上午十點到下午兩點",
            "金": "下午三點到五點",
            "土": "早上八點到十點",
        }

        ELEMENT_AVOID = {
            "日": "傍晚後能量消退，重要決定不要拖到晚上",
            "月": "正午前後能量弱，避免安排正式場合",
            "火": "晚間容易浮躁，不適合需要耐心的事",
            "水": "下午注意力容易下降，複雜事務排上午",
            "木": "傍晚後能量分散，日落前完成重要的事",
            "金": "上午能量還沒到位，重要的事排下午",
            "土": "午後容易拖延，早辦早好",
        }

        return {
            "best_time": ELEMENT_PEAK.get(day_element, "上午"),
            "avoid_time": ELEMENT_AVOID.get(day_element, "")
        }

    def _get_pair_time_tip(
        self,
        relation1_type: str,
        relation2_type: str,
        day_element: str,
        _element1: str,
        _element2: str,
        action_key: str
    ) -> dict:
        """根據雙方宿曜關係和七曜元素生成時段建議"""

        # 七曜元素對應的能量高峰時段
        ELEMENT_PEAK_HOURS = {
            "日": {"peak": "10:00-12:00", "label": "上午十點到十二點", "note": "日曜能量在正午前最強，適合正式場合"},
            "月": {"peak": "18:00-21:00", "label": "下午六點到九點", "note": "月曜能量在日落後漸強，適合輕鬆的互動"},
            "火": {"peak": "14:00-16:00", "label": "下午兩點到四點", "note": "火曜能量在午後達到高峰，適合需要活力的活動"},
            "水": {"peak": "09:00-11:00", "label": "上午九點到十一點", "note": "水曜能量在早晨清澈穩定，適合需要思考的事務"},
            "木": {"peak": "10:00-14:00", "label": "上午十點到下午兩點", "note": "木曜能量持續時間長，上午到午後都適合行動"},
            "金": {"peak": "15:00-17:00", "label": "下午三點到五點", "note": "金曜能量在午後偏晚時段最集中，適合簽約和決策"},
            "土": {"peak": "08:00-10:00", "label": "早上八點到十點", "note": "土曜能量在清晨最穩定，早起行動效果最好"},
        }

        # 避免的時段
        ELEMENT_AVOID_HOURS = {
            "日": "傍晚後日曜能量消退，重要決定不要拖到晚上",
            "月": "中午前後月曜能量最弱，避免安排正式場合",
            "火": "晚間火曜容易讓人浮躁，不適合需要耐心的溝通",
            "水": "下午容易疲倦，注意力下降，避免處理複雜事務",
            "木": "傍晚後能量分散，盡量在日落前完成重要的事",
            "金": "上午金曜能量還沒到位，重要的事排在下午比較好",
            "土": "午後土曜能量變得沉重，容易拖延，早辦早好",
        }

        peak = ELEMENT_PEAK_HOURS.get(day_element, ELEMENT_PEAK_HOURS["土"])
        avoid = ELEMENT_AVOID_HOURS.get(day_element, "")

        # 根據行動類型微調建議
        ACTION_TIME_TIPS = {
            "date": "約會選在能量高峰前後，兩人的互動會更自然放鬆。不用趕時間，留充裕的相處空間",
            "dinner": "晚餐約會選在六點半到七點入座。太早趕、太晚餓，剛好的時間讓談話更從容",
            "trip": "出發時間盡量排在上午。早出門的旅途心情比較好，也有更多時間享受目的地",
            "gift": "挑禮物選在自己狀態好的時段去，你的品味判斷力跟精神狀態直接相關",
            "meeting": "正式場合排在雙方都精神好的時段。開場前十分鐘到場，從容的態度是最好的開場白",
            "denpo": "傳法儀式排在早課後的上午時段，師徒雙方精神最清明。寅時起身淨身，辰時開壇最為如法",
            "kanjo": "灌頂以上午為宜，日光充足時結界清淨。儀式前師徒都要靜坐片刻收攝身心",
            "jukai": "授戒宜在上午，受者心神安定時理解戒律最為深入。儀式後留時間讓受者提問",
            "teaching": "教學選雙方都精神集中的時段。上午講義理、下午練實修，效率最好",
            "register": "登記和簽約選上午，精神清醒而且處理完還有一整天可以慶祝",
            "wedding": "婚禮儀式排在上午到中午，賓客的精神和心情都在最好的狀態",
            "engagement": "訂婚是溫馨的場合，下午茶時段或晚餐時段都適合，選雙方家庭方便的時間",
            "parent_visit": "拜訪長輩選上午或午後，避開午休時段。帶一份對方喜歡的點心，比空手更體面",
            "family_dinner": "家庭聚餐選週末中午或傍晚。人齊比時間完美更重要",
        }

        tip = ACTION_TIME_TIPS.get(action_key, "")

        # 如果雙方都是好關係，給更積極的提示
        good_relations = {"eishin", "gyotai", "mei", "yusui"}
        if relation1_type in good_relations and relation2_type in good_relations:
            if not tip:
                tip = f"雙方能量都處於良好狀態，{peak['label']}行動效果最好"
        elif not tip:
            tip = peak["note"]

        return {
            "best_time": peak["label"],
            "avoid_time": avoid,
            "tip": tip
        }

    def get_pair_lucky_days(
        self,
        birth_date1: date,
        birth_date2: date,
        relation_type: str,
        days_ahead: int = 30
    ) -> dict:
        """
        計算雙人吉日

        根據兩人的本命宿和關係類型，計算適合共同行動的吉日。

        Args:
            birth_date1: 第一人（自己）的生日
            birth_date2: 第二人（收藏對象）的生日
            relation_type: 關係類型（dating/spouse/parent/family/friend）
            days_ahead: 查詢未來幾天（預設 30）

        Returns:
            各項吉日列表
        """
        from datetime import timedelta

        # 驗證關係類型
        if relation_type not in self.PAIR_LUCKY_ACTIONS:
            raise ValueError(f"無效的關係類型: {relation_type}")

        relation_config = self.PAIR_LUCKY_ACTIONS[relation_type]

        # 取得雙方本命宿資料
        mansion1 = self.get_mansion(birth_date1)
        mansion2 = self.get_mansion(birth_date2)

        # 計算兩人相性
        compatibility = self.calculate_compatibility(birth_date1, birth_date2)

        today = date.today()
        fortune_data = self._load_fortune_data()

        # 為每個行動項目計算吉日
        results = []
        for action in relation_config["actions"]:
            lucky_days = []
            favor_relations = action["favor_relations"]
            favor_score = action["favor_score"]

            for i in range(days_ahead):
                check_date = today + timedelta(days=i)

                # 計算雙方當日運勢
                fortune1 = self.calculate_daily_fortune(birth_date1, check_date)
                fortune2 = self.calculate_daily_fortune(birth_date2, check_date)

                # 取雙方運勢平均
                avg_score = (fortune1["fortune"]["overall"] + fortune2["fortune"]["overall"]) // 2

                # 統一品質評估（雙方都檢查）
                q1 = self._evaluate_day_quality(fortune1, action["key"])
                q2 = self._evaluate_day_quality(fortune2, action["key"])

                if q1["excluded"] or q2["excluded"]:
                    continue

                # 取得當日資訊
                weekday = check_date.weekday()
                jp_weekday = (weekday + 1) % 7
                day_info = fortune_data["weekday_elements"][str(jp_weekday)]
                day_name = day_info["name"]
                day_element = day_info["element"]

                # 計算當日宿（修正後宿位）
                day_mansion_index = self._get_corrected_mansion_index(check_date)

                # 計算雙方與當日宿的關係
                relation1 = self.get_relation_type(mansion1["index"], day_mansion_index)
                relation2 = self.get_relation_type(mansion2["index"], day_mansion_index)

                # 判斷是否吉日
                is_lucky = False
                lucky_reason = ""

                # 雙方都是好關係
                if relation1["type"] in favor_relations and relation2["type"] in favor_relations:
                    is_lucky = True
                    lucky_reason = f"雙方與當日宿同時形成{relation1['name']}/{relation2['name']}的良好關係，能量場高度契合，適合一起{action['name']}"
                # 至少一方是好關係，另一方不是凶日
                elif (relation1["type"] in favor_relations and relation2["type"] not in ["ankai", "kisei"]) or \
                     (relation2["type"] in favor_relations and relation1["type"] not in ["ankai", "kisei"]):
                    if avg_score >= favor_score:
                        is_lucky = True
                        lucky_reason = f"雙方運勢平均 {avg_score} 分，加上其中一方與當日宿關係良好，整體氛圍適合{action['name']}"
                # 雙方運勢都很好
                elif avg_score >= favor_score + 10:
                    if relation1["type"] not in ["ankai", "kisei"] and relation2["type"] not in ["ankai", "kisei"]:
                        is_lucky = True
                        lucky_reason = f"雙方運勢平均高達 {avg_score} 分，兩人的狀態都處於高峰期，很適合一起{action['name']}"

                # master 關係額外規則：傳法/灌頂/授戒雙方都要 >= 60
                if is_lucky and relation_type == "master" and action["key"] in ("denpo", "kanjo", "jukai"):
                    if fortune1["fortune"]["overall"] < 60 or fortune2["fortune"]["overall"] < 60:
                        is_lucky = False

                if is_lucky and len(lucky_days) < 5:
                    rating = "大吉" if avg_score >= 85 else "吉" if avg_score >= 70 else "中吉"

                    # 品質調整：取雙方中較差的 rating_shift
                    min_shift = min(q1["rating_shift"], q2["rating_shift"])
                    if min_shift != 0:
                        rating = self._shift_rating_name(rating, min_shift)

                    # 合併衝突/加持標記
                    all_conflicts = list(set(q1["conflicts"] + q2["conflicts"]))
                    all_boosts = list(set(q1["boosts"] + q2["boosts"]))

                    # 時段建議
                    time_tip = self._get_pair_time_tip(
                        relation1["type"], relation2["type"],
                        day_element, mansion1["element"], mansion2["element"],
                        action["key"]
                    )

                    day_entry: dict = {
                        "date": check_date.isoformat(),
                        "weekday": day_name,
                        "score": avg_score,
                        "rating": rating,
                        "reason": lucky_reason,
                        "best_time": time_tip["best_time"],
                        "avoid_time": time_tip["avoid_time"],
                        "tip": time_tip["tip"]
                    }
                    if all_conflicts:
                        day_entry["conflicts"] = all_conflicts
                    if all_boosts:
                        day_entry["boosts"] = all_boosts

                    lucky_days.append(day_entry)

            results.append({
                "action": action["key"],
                "name": action["name"],
                "lucky_days": lucky_days
            })

        return {
            "relation_type": relation_type,
            "relation_name": relation_config["name"],
            "person1": {
                "mansion": mansion1["name_jp"],
                "reading": mansion1["reading"],
                "element": mansion1["element"]
            },
            "person2": {
                "mansion": mansion2["name_jp"],
                "reading": mansion2["reading"],
                "element": mansion2["element"]
            },
            "compatibility": {
                "relation": compatibility["relation"]["name"],
                "score": compatibility["score"],
                "description": compatibility["relation"]["description"]
            },
            "actions": results
        }

    # ==================== 吉日月曆 ====================

    # 雙人吉日白話建議模板
    # 依關係品質(good/neutral/bad) × action 分類
    PAIR_ADVICE_TEMPLATES = {
        # === good (eishin/gyotai) ===
        ("good", "date"): {
            "summary": "今天你們的互動會特別自然，不用刻意找話題也能聊得開心。氣氛好到連沉默都是舒服的。",
            "do": ["分享最近的想法或感受", "嘗試沒去過的地方", "拍幾張合照留念"],
            "avoid": ["催促對方做決定", "提起讓對方有壓力的話題"]
        },
        ("good", "confession"): {
            "summary": "對方今天對你的好感度比平時高，你說的話會被認真聽進去。直接表達的效果比暗示好。",
            "do": ["找一個兩人都放鬆的場合", "用簡單的話說出你的感受", "給對方回應的空間"],
            "avoid": ["在公共場所造成壓力", "準備太長的台詞反而不自然"]
        },
        ("good", "meet_parents"): {
            "summary": "長輩今天的接受度比較高，你的表現會被用善意的眼光看待。放鬆做自己就好。",
            "do": ["帶一份用心挑選的伴手禮", "主動幫忙但不過度表現", "真誠地回答問題"],
            "avoid": ["過度緊張反而讓氣氛僵硬", "話太多或太少都不好"]
        },
        ("good", "engagement"): {
            "summary": "雙方家庭的能量場今天特別和諧，談條件時容易找到讓雙方都舒服的平衡點。",
            "do": ["事前跟雙方確認期待", "保持從容的節奏", "記錄重要的約定"],
            "avoid": ["在細節上過度計較", "讓任何一方覺得被冷落"]
        },
        ("good", "register"): {
            "summary": "今天登記的能量場特別穩定，這個日期會成為你們回憶裡溫暖的起點。",
            "do": ["帶一件有紀念意義的小物", "儀式結束後一起吃頓好的", "手寫一段話給對方"],
            "avoid": ["行程排太滿反而匆忙", "忘記享受這個時刻"]
        },
        ("good", "wedding"): {
            "summary": "婚禮當天的氛圍會很好，賓客也能感受到你們的幸福。專心享受就好。",
            "do": ["提前跟攝影師溝通想要的畫面", "留時間跟重要的人說話", "接受不完美的小插曲"],
            "avoid": ["因為小細節影響心情", "行程太趕讓自己疲憊"]
        },
        ("good", "travel"): {
            "summary": "旅途中你們的默契會特別好，臨時改行程也能玩得開心。放輕鬆享受過程。",
            "do": ["讓彼此都有想去的地方", "留一些隨性探索的時間", "一起嘗試新事物"],
            "avoid": ["把行程排得太緊", "一個人決定所有事情"]
        },
        ("good", "discussion"): {
            "summary": "今天你們的溝通效率特別高，複雜的事情也能談得清楚。趁這天把重要的事情攤開來聊。",
            "do": ["先聽完對方的想法再回應", "把結論記下來", "感謝對方的坦誠"],
            "avoid": ["打斷對方的話", "用情緒取代論點"]
        },
        ("good", "visit"): {
            "summary": "今天去看長輩的氛圍會特別溫馨，你的陪伴讓對方感覺被重視。",
            "do": ["帶對方喜歡的東西", "多聽少說", "拍幾張照片記錄"],
            "avoid": ["趕時間的感覺", "只顧著滑手機"]
        },
        ("good", "gift"): {
            "summary": "今天送禮的時機很好，對方收到會特別開心。用心比貴重重要。",
            "do": ["挑選對方真正需要或喜歡的", "附上一句手寫的話", "當面送比寄送更有溫度"],
            "avoid": ["送太貴的東西反而造成壓力", "敷衍了事"]
        },
        ("good", "gathering"): {
            "summary": "今天的聚會氣氛會很好，大家都處於放鬆的狀態，容易聊出有意思的話題。",
            "do": ["選一個大家都方便的地點", "主動帶動話題", "拍張團體照"],
            "avoid": ["只跟特定的人聊天", "低頭看手機"]
        },
        ("good", "collaboration"): {
            "summary": "合作的默契今天特別好，分工明確之後效率會很高。是啟動新計畫的好時機。",
            "do": ["先確認雙方的目標一致", "各自負責擅長的部分", "定期回報進度"],
            "avoid": ["模糊的分工", "單方面改變方向"]
        },
        # === neutral (yusui/kisei/mei) ===
        ("neutral", "date"): {
            "summary": "今天的約會節奏不會太快也不會太慢，適合好好認識彼此。不用刻意製造驚喜。",
            "do": ["選一個安靜舒服的地方", "聊一些平時沒機會聊的話題", "保持自然的互動"],
            "avoid": ["安排太多活動", "期待值拉太高"]
        },
        ("neutral", "confession"): {
            "summary": "對方今天的心情平穩，會理性地考慮你說的話。結果不一定馬上有，但會被認真對待。",
            "do": ["選一個不趕時間的場合", "說完之後給對方思考的空間", "不管結果如何保持風度"],
            "avoid": ["用太戲劇化的方式", "要求對方馬上回答"]
        },
        ("neutral", "meet_parents"): {
            "summary": "長輩今天的態度中性偏正面，你的表現不需要特別完美，但基本禮貌要到位。",
            "do": ["準時到場", "回答問題時誠懇", "表現出你對關係的重視"],
            "avoid": ["過度謙虛或過度表現", "忽略任何一方家長"]
        },
        ("neutral", "engagement"): {
            "summary": "條件的溝通需要多一些耐心，雙方可能有不同的想法，但都能透過討論找到共識。",
            "do": ["提前準備好想討論的項目", "保持開放的態度", "把重要的約定寫下來"],
            "avoid": ["堅持己見不讓步", "在小事上花太多時間"]
        },
        ("neutral", "register"): {
            "summary": "登記的流程會順利完成，雖然不會有太多戲劇性的感動，但踏實的幸福感是真實的。",
            "do": ["把流程確認清楚", "帶齊需要的文件", "事後安排一個小慶祝"],
            "avoid": ["把這天跟其他雜事排在一起", "忘記留紀念照"]
        },
        ("neutral", "wedding"): {
            "summary": "婚禮會順利進行，可能有一兩個小插曲但不影響整體。事前的準備越充分越好。",
            "do": ["再確認一次流程表", "指派一個信任的人當天協調", "專注在你們自己的幸福"],
            "avoid": ["當天才處理遺漏的事情", "讓瑣事消耗你的精力"]
        },
        ("neutral", "travel"): {
            "summary": "旅途大致順利，偶爾可能需要調整計畫。保持彈性、互相配合就好。",
            "do": ["備好替代方案", "輪流決定行程", "不舒服就直說"],
            "avoid": ["把行程排到分秒不差", "一個人承擔所有決策"]
        },
        ("neutral", "discussion"): {
            "summary": "溝通需要比平時多一點耐心，但只要雙方都願意聽，就能找到解法。",
            "do": ["把想說的重點先整理好", "用「我覺得」而非「你應該」", "確認彼此的理解一致"],
            "avoid": ["帶著情緒開口", "翻舊帳"]
        },
        ("neutral", "visit"): {
            "summary": "探訪的氣氛平穩，對方會覺得被關心。不用準備太多，人到就是心意。",
            "do": ["帶一些日常的小東西", "聊聊近況", "幫忙做一些小事"],
            "avoid": ["待太久反而讓對方累", "只聊自己的事"]
        },
        ("neutral", "gift"): {
            "summary": "送禮的效果中規中矩，重點在於你有想到對方，而非禮物多貴重。",
            "do": ["選實用的東西", "包裝稍微用心一點", "看對方的反應調整"],
            "avoid": ["送跟對方需求無關的東西", "期待對方有很大的反應"]
        },
        ("neutral", "gathering"): {
            "summary": "聚會的氣氛需要有人帶動，但只要暖場起來就會越來越熱絡。",
            "do": ["準備一兩個話題備用", "注意比較安靜的人", "時間不用太長"],
            "avoid": ["讓場面冷掉太久", "只聊工作或八卦"]
        },
        ("neutral", "collaboration"): {
            "summary": "合作推進的速度中等，需要多確認方向是否一致。多花一點時間溝通是值得的。",
            "do": ["開始前先對齊目標", "遇到分歧馬上討論", "階段性確認成果"],
            "avoid": ["各做各的不溝通", "想當然以為對方理解"]
        },
        # === bad (ankai) ===
        ("bad", "date"): {
            "summary": "今天的互動容易有摩擦，可能是雞毛蒜皮的小事引發不必要的爭執。如果能改天更好。",
            "do": ["選輕鬆不需要做決定的活動", "對方說什麼先不急著反駁", "控制自己的情緒"],
            "avoid": ["去人太多或太吵的地方", "討論敏感話題", "期待太高"]
        },
        ("bad", "confession"): {
            "summary": "今天告白的成功率偏低，對方的接收狀態不太理想。建議等一個更好的時機。",
            "do": ["先按兵不動", "維持正常的互動就好", "觀察對方的狀態"],
            "avoid": ["衝動表白", "用訊息代替面對面", "把對方的冷淡當拒絕"]
        },
        ("bad", "meet_parents"): {
            "summary": "長輩今天的心情可能不太穩定，容易對小事挑剔。如果能延期到更好的日子是首選。",
            "do": ["降低期待值", "保持最基本的禮貌", "不用刻意表現"],
            "avoid": ["說太多自己的事", "急著讓對方喜歡你", "回嘴或辯解"]
        },
        ("bad", "travel"): {
            "summary": "旅途中容易出現延誤、意見不合或突發狀況。多預留緩衝時間，互相包容很重要。",
            "do": ["準備備案", "東西帶齊", "有狀況先深呼吸"],
            "avoid": ["趕行程", "把責任推給對方", "因為小事發脾氣"]
        },
        ("bad", "discussion"): {
            "summary": "今天的溝通容易雞同鴨講，說了半天還是各說各話。建議只處理緊急的事，其他改天談。",
            "do": ["只講最重要的一兩件事", "多用書面確認", "保留彈性"],
            "avoid": ["一次處理太多議題", "用指責的語氣", "在情緒不好時硬聊"]
        },
        ("bad", "visit"): {
            "summary": "今天拜訪的氣氛可能有點緊繃，對方的狀態不太好。簡短問候就好。",
            "do": ["控制拜訪時間", "帶一些對方需要的東西", "少說多做"],
            "avoid": ["待太久", "提起讓對方不舒服的話題", "強迫互動"]
        },
        ("bad", "gathering"): {
            "summary": "聚會中可能有些微妙的氣氛，有人心情不好或話不投機。保持低調就好。",
            "do": ["跟聊得來的人互動", "氣氛不對就早點離開", "不用勉強融入"],
            "avoid": ["挑起爭議話題", "喝太多", "在背後議論"]
        },
        ("bad", "collaboration"): {
            "summary": "合作的摩擦係數今天偏高，容易在方向或細節上產生分歧。能延後就延後。",
            "do": ["用書面確認重要決定", "保持專業態度", "有分歧先暫停"],
            "avoid": ["一意孤行", "在情緒上跟對方對抗", "做出無法挽回的決定"]
        },
        ("bad", "gift"): {
            "summary": "今天送禮的效果可能不如預期，對方的反應偏平淡。不是你的問題，是時機不對。",
            "do": ["如果一定要送就選實用的", "不要期待太大的反應", "改天補送效果更好"],
            "avoid": ["送太貴的東西", "要求對方馬上拆開"]
        },
        ("bad", "engagement"): {
            "summary": "今天談條件容易卡住，雙方的期待落差比較大。建議另找日子再繼續。",
            "do": ["先確認哪些是雙方的底線", "不用急著一次談完", "保持尊重"],
            "avoid": ["最後通牒式的談判", "在情緒不好時做決定", "讓任何一方感到被施壓"]
        },
        ("bad", "register"): {
            "summary": "建議換到更好的日期登記。如果非今天不可，保持平常心、專注在你們的決定本身。",
            "do": ["簡單完成流程", "事後安排一個放鬆的活動", "不要被小事影響心情"],
            "avoid": ["當天處理其他壓力大的事", "過度在意細節"]
        },
        ("bad", "wedding"): {
            "summary": "婚禮日期建議慎選。如果已經無法更改，做好萬全準備就能把風險降到最低。",
            "do": ["所有環節再確認一次", "多準備一兩個備案", "指定一個應急聯絡人"],
            "avoid": ["臨時更改流程", "讓自己承擔所有壓力"]
        },
        # === master 師徒 ===
        ("good", "denpo"): {
            "summary": "師徒之間的法脈傳承在今天特別順暢，弟子的根器和師父的加持力都處於高峰。",
            "do": ["提前齋戒淨身", "選清淨莊嚴的場所", "師徒雙方先靜坐收攝"],
            "avoid": ["倉促行事", "心緒未定時強行開壇"]
        },
        ("good", "kanjo"): {
            "summary": "灌頂的因緣殊勝，受者今天的領受力特別強，加持力容易相應。",
            "do": ["提前準備壇城法器", "受者前夜持戒清淨", "儀式後留時間回向"],
            "avoid": ["受者身心疲憊時勉強進行", "省略必要的前行"]
        },
        ("good", "jukai"): {
            "summary": "授戒的時機很好，受者今天對戒律的理解力和發願心都處於最佳狀態。",
            "do": ["事前講解戒條內容", "確認受者的發心", "儀式莊嚴如法"],
            "avoid": ["趕時間導致受者理解不足", "忽略受者的疑問"]
        },
        ("good", "teaching"): {
            "summary": "教學的效果今天特別好，弟子的專注力和理解力都比平時高。適合講深一點的內容。",
            "do": ["備好教材和實修指導", "觀察弟子的理解程度", "留時間答疑"],
            "avoid": ["一次講太多消化不了", "只講理論不給實修方向"]
        },
        ("neutral", "denpo"): {
            "summary": "傳法的條件中等，師徒雙方的狀態都還可以。做好準備工作能補足時機上的不足。",
            "do": ["充分的前行準備", "師徒先共修暖身", "確認雙方身心狀態"],
            "avoid": ["隨意開壇", "忽略準備工作"]
        },
        ("neutral", "kanjo"): {
            "summary": "灌頂可以進行但要多花心思在前行上。受者的狀態需要用準備工作來調整到位。",
            "do": ["加強前行修法", "確認受者的身心準備", "儀式按部就班"],
            "avoid": ["省略前行步驟", "對受者的準備度要求太低"]
        },
        ("neutral", "jukai"): {
            "summary": "授戒可以進行，受者的接受度中等。多花時間在戒條講解上會有更好的效果。",
            "do": ["逐條講解戒律", "給受者充分的思考時間", "確認受者真正理解"],
            "avoid": ["形式化地走流程", "忽略受者的個別狀況"]
        },
        ("neutral", "teaching"): {
            "summary": "教學效果普通，弟子的吸收速度中等。以基礎和複習為主比較有效率。",
            "do": ["複習上次的內容", "用具體例子說明", "進度不用太快"],
            "avoid": ["講全新的難度高的內容", "一直講不給弟子消化的時間"]
        },
        ("bad", "denpo"): {
            "summary": "傳法的時機不佳，師徒雙方的能量場容易干擾。強烈建議另擇吉日。",
            "do": ["延期到更好的日子", "如果不能延期就加強護摩前行", "師徒各自先調整狀態"],
            "avoid": ["在能量不穩定時傳承重要法脈", "忽略不吉的徵兆"]
        },
        ("bad", "kanjo"): {
            "summary": "灌頂建議改期。今天的能量場不利於加持力的傳遞，受者的領受也容易打折扣。",
            "do": ["改期是最好的選擇", "非改不可就大幅加強前行", "師父先獨修穩定自身"],
            "avoid": ["勉強進行形式上的灌頂", "在師父或受者狀態不佳時開壇"]
        },
        ("bad", "jukai"): {
            "summary": "授戒建議延期。受者今天的心念不夠穩定，勉強受戒反而容易產生障礙。",
            "do": ["另擇吉日", "讓受者多準備一段時間", "先進行預備的學戒課程"],
            "avoid": ["趕進度強行授戒", "忽略受者的身心狀態"]
        },
        ("bad", "teaching"): {
            "summary": "教學效果偏差，弟子的專注力和理解力今天都比較低。輕量的複習比硬教新東西好。",
            "do": ["輕鬆地複習舊內容", "聊一些修行體會", "早點結束讓弟子休息"],
            "avoid": ["講新的重要內容", "因為弟子理解慢而不耐煩"]
        },
    }

    def _get_pair_advice(self, relation_quality: str, action_key: str) -> Optional[dict]:
        """取得雙人吉日的白話建議"""
        advice = self.PAIR_ADVICE_TEMPLATES.get((relation_quality, action_key))
        if advice:
            return advice
        # 通用 fallback
        fallback = self.PAIR_ADVICE_TEMPLATES.get((relation_quality, "date"))
        return fallback

    @staticmethod
    def _classify_relation_quality(relation_type: str) -> str:
        """將宿曜關係分為 good/neutral/bad 三檔"""
        if relation_type in ("eishin", "gyotai"):
            return "good"
        elif relation_type in ("ankai",):
            return "bad"
        else:  # yusui, kisei, mei
            return "neutral"

    def get_lucky_days_calendar(
        self,
        birth_date: date,
        year: int,
        month: int,
        categories: list[str] | None = None
    ) -> dict:
        """
        取得整月吉日月曆（個人）

        掃描指定月份每一天，回傳以日期為 key 的吉日地圖。

        Args:
            birth_date: 西曆生日
            year: 年份
            month: 月份 (1-12)
            categories: 篩選的分類列表，None = 全部

        Returns:
            月曆吉日資料
        """
        import calendar as cal
        from datetime import timedelta

        mansion = self.get_mansion(birth_date)
        user_element = mansion["element"]
        user_index = mansion["index"]
        fortune_data = self._load_fortune_data()

        # 取得當月天數
        _, days_in_month = cal.monthrange(year, month)
        all_cats = self.LUCKY_DAY_CATEGORIES
        target_cats = {k: v for k, v in all_cats.items() if not categories or k in categories}

        days_map: dict[str, list] = {}
        mansion_names = {11: "室宿", 8: "女宿", 21: "鬼宿"}

        for day_num in range(1, days_in_month + 1):
            check_date = date(year, month, day_num)

            # 計算當日運勢
            daily_fortune = self.calculate_daily_fortune(birth_date, check_date)
            score = daily_fortune["fortune"]["overall"]
            day_level = daily_fortune["fortune"].get("level", "chukichi")

            # 取得當日資訊
            weekday = check_date.weekday()
            jp_weekday = (weekday + 1) % 7
            day_element = fortune_data["weekday_elements"][str(jp_weekday)]["element"]
            day_name = fortune_data["weekday_elements"][str(jp_weekday)]["name"]

            # 計算當日宿
            day_mansion_index = self._get_corrected_mansion_index(check_date)
            relation = self.get_relation_type(user_index, day_mansion_index)
            relation_type = relation["type"]

            date_key = check_date.isoformat()
            day_results = []

            # 統一品質評估（每日只算一次，action 無關的部分共用）
            quality_cache: dict[str, dict] = {}

            for cat_key, cat_config in target_cats.items():
                for act_key, action_config in cat_config["actions"].items():
                    favor_relations = action_config.get("favor_relations", ["eishin"])
                    avoid_relations = action_config.get("avoid_relations", ["ankai", "kisei"])
                    favor_score = action_config.get("favor_score", 70)
                    favor_weekdays = action_config.get("favor_weekdays", None)
                    favor_mansions = action_config.get("favor_mansions", None)

                    # 品質評估（含凌犯/壊の日/羅刹日/暗黒等排除）
                    if act_key not in quality_cache:
                        quality_cache[act_key] = self._evaluate_day_quality(daily_fortune, act_key)
                    quality = quality_cache[act_key]

                    if quality["excluded"]:
                        continue

                    # action 特有排除
                    if relation_type in avoid_relations:
                        continue
                    avoid_weekdays = action_config.get("avoid_weekdays", None)
                    if avoid_weekdays and weekday in avoid_weekdays:
                        continue
                    if action_config.get("avoid_birth_mansion") and day_mansion_index == user_index:
                        continue
                    if day_level in ("shokyo", "kyo"):
                        continue

                    # 判斷吉日條件
                    is_lucky = False
                    lucky_reason = ""

                    if relation_type in favor_relations:
                        is_lucky = True
                        lucky_reason = f"{relation['name']}日，{self._get_relation_benefit(relation_type, act_key)}"
                    elif favor_mansions and day_mansion_index in favor_mansions:
                        is_lucky = True
                        m_name = mansion_names.get(day_mansion_index, f"index {day_mansion_index}")
                        lucky_reason = f"當日宿為{m_name}，傳統上特別適合{action_config['name']}"
                    elif day_element == user_element and score >= favor_score:
                        is_lucky = True
                        lucky_reason = f"{day_name}（{day_element}曜）與你的本命元素相同，能量共振"
                    elif self._is_generating(day_element, user_element) and score >= favor_score:
                        is_lucky = True
                        lucky_reason = f"{day_name}的{day_element}曜能量滋養你的本命元素，形成相生"
                    elif score >= favor_score + 5:
                        if favor_weekdays and weekday in favor_weekdays:
                            is_lucky = True
                            lucky_reason = f"運勢{score}分，加上{day_name}適合{action_config['name']}"
                        elif score >= favor_score + 10:
                            is_lucky = True
                            lucky_reason = f"運勢高達{score}分，適合處理重要事務"

                    if is_lucky:
                        rating = self.LEVEL_NAMES.get(day_level, {"zh": "中吉"})["zh"]
                        if quality["rating_shift"] != 0:
                            rating = self._shift_rating_name(rating, quality["rating_shift"])
                        time_tip = self._get_personal_time_tip(day_element, user_element, act_key)

                        day_entry: dict = {
                            "category": cat_key,
                            "category_name": cat_config["name"],
                            "action": act_key,
                            "action_name": action_config["name"],
                            "score": score,
                            "rating": rating,
                            "reason": lucky_reason,
                            "best_time": time_tip["best_time"],
                            "avoid_time": time_tip["avoid_time"]
                        }
                        if quality["conflicts"]:
                            day_entry["conflicts"] = quality["conflicts"]
                        if quality["boosts"]:
                            day_entry["boosts"] = quality["boosts"]

                        day_results.append(day_entry)

            if day_results:
                days_map[date_key] = day_results

        return {
            "year": year,
            "month": month,
            "your_mansion": {
                "name_jp": mansion["name_jp"],
                "reading": mansion["reading"],
                "element": user_element,
                "index": user_index
            },
            "days": days_map
        }

    def get_pair_lucky_days_calendar(
        self,
        birth_date1: date,
        birth_date2: date,
        relation_type: str,
        year: int,
        month: int
    ) -> dict:
        """
        取得整月雙人吉日月曆

        掃描指定月份每一天，回傳以日期為 key 的吉日地圖，每個吉日附帶白話建議。

        Args:
            birth_date1: 第一人（自己）的生日
            birth_date2: 第二人（收藏對象）的生日
            relation_type: 關係類型（dating/spouse/parent/family/friend）
            year: 年份
            month: 月份 (1-12)

        Returns:
            月曆雙人吉日資料
        """
        import calendar as cal
        from datetime import timedelta

        if relation_type not in self.PAIR_LUCKY_ACTIONS:
            raise ValueError(f"無效的關係類型: {relation_type}")

        relation_config = self.PAIR_LUCKY_ACTIONS[relation_type]

        mansion1 = self.get_mansion(birth_date1)
        mansion2 = self.get_mansion(birth_date2)
        compatibility = self.calculate_compatibility(birth_date1, birth_date2)

        fortune_data = self._load_fortune_data()
        _, days_in_month = cal.monthrange(year, month)

        days_map: dict[str, list] = {}

        for day_num in range(1, days_in_month + 1):
            check_date = date(year, month, day_num)

            # 計算雙方當日運勢
            fortune1 = self.calculate_daily_fortune(birth_date1, check_date)
            fortune2 = self.calculate_daily_fortune(birth_date2, check_date)
            avg_score = (fortune1["fortune"]["overall"] + fortune2["fortune"]["overall"]) // 2

            # 取得當日資訊
            weekday = check_date.weekday()
            jp_weekday = (weekday + 1) % 7
            day_info = fortune_data["weekday_elements"][str(jp_weekday)]
            day_name = day_info["name"]
            day_element = day_info["element"]

            day_mansion_index = self._get_corrected_mansion_index(check_date)

            relation1 = self.get_relation_type(mansion1["index"], day_mansion_index)
            relation2 = self.get_relation_type(mansion2["index"], day_mansion_index)

            date_key = check_date.isoformat()
            day_results = []

            for action in relation_config["actions"]:
                favor_relations = action["favor_relations"]
                favor_score = action["favor_score"]

                # 統一品質評估（雙方都檢查）
                dq1 = self._evaluate_day_quality(fortune1, action["key"])
                dq2 = self._evaluate_day_quality(fortune2, action["key"])

                if dq1["excluded"] or dq2["excluded"]:
                    continue

                is_lucky = False
                lucky_reason = ""

                if relation1["type"] in favor_relations and relation2["type"] in favor_relations:
                    is_lucky = True
                    lucky_reason = f"雙方與當日宿同時形成{relation1['name']}/{relation2['name']}的良好關係，能量場高度契合"
                elif (relation1["type"] in favor_relations and relation2["type"] not in ["ankai", "kisei"]) or \
                     (relation2["type"] in favor_relations and relation1["type"] not in ["ankai", "kisei"]):
                    if avg_score >= favor_score:
                        is_lucky = True
                        lucky_reason = f"雙方運勢平均 {avg_score} 分，其中一方與當日宿關係良好"
                elif avg_score >= favor_score + 10:
                    if relation1["type"] not in ["ankai", "kisei"] and relation2["type"] not in ["ankai", "kisei"]:
                        is_lucky = True
                        lucky_reason = f"雙方運勢平均高達 {avg_score} 分，狀態都處於高峰期"

                # master 關係額外規則
                if is_lucky and relation_type == "master" and action["key"] in ("denpo", "kanjo", "jukai"):
                    if fortune1["fortune"]["overall"] < 60 or fortune2["fortune"]["overall"] < 60:
                        is_lucky = False

                if is_lucky:
                    rating = "大吉" if avg_score >= 85 else "吉" if avg_score >= 70 else "中吉"

                    # 品質調整
                    min_shift = min(dq1["rating_shift"], dq2["rating_shift"])
                    if min_shift != 0:
                        rating = self._shift_rating_name(rating, min_shift)

                    all_conflicts = list(set(dq1["conflicts"] + dq2["conflicts"]))
                    all_boosts = list(set(dq1["boosts"] + dq2["boosts"]))

                    time_tip = self._get_pair_time_tip(
                        relation1["type"], relation2["type"],
                        day_element, mansion1["element"], mansion2["element"],
                        action["key"]
                    )

                    # 白話建議
                    rq1 = self._classify_relation_quality(relation1["type"])
                    rq2 = self._classify_relation_quality(relation2["type"])
                    quality_order = {"bad": 0, "neutral": 1, "good": 2}
                    final_quality = rq1 if quality_order[rq1] <= quality_order[rq2] else rq2
                    advice = self._get_pair_advice(final_quality, action["key"])

                    day_entry: dict = {
                        "action": action["key"],
                        "name": action["name"],
                        "score": avg_score,
                        "rating": rating,
                        "reason": lucky_reason,
                        "best_time": time_tip["best_time"],
                        "avoid_time": time_tip["avoid_time"],
                        "tip": time_tip["tip"],
                        "advice": advice
                    }
                    if all_conflicts:
                        day_entry["conflicts"] = all_conflicts
                    if all_boosts:
                        day_entry["boosts"] = all_boosts

                    day_results.append(day_entry)

            if day_results:
                days_map[date_key] = day_results

        return {
            "year": year,
            "month": month,
            "person1": {
                "mansion": mansion1["name_jp"],
                "reading": mansion1["reading"],
                "element": mansion1["element"]
            },
            "person2": {
                "mansion": mansion2["name_jp"],
                "reading": mansion2["reading"],
                "element": mansion2["element"]
            },
            "compatibility": {
                "relation": compatibility["relation"]["name"],
                "score": compatibility["score"],
                "description": compatibility["relation"]["description"]
            },
            "days": days_map
        }


    def check_ryouhan_period(self, target_date: date) -> Optional[dict]:
        """
        判定指定日期是否在凌犯期間（七曜陵逼）

        根據該日期所在農曆月的朔日（初一）七曜，查表判定。
        凌犯期間內甘露日→凶、羅刹日→吉（吉凶逆轉）。

        Args:
            target_date: 西曆日期

        Returns:
            凌犯期間資訊（若不在期間內則返回 None）
        """
        # 注：閏月時 lunar_m 仍為該月數字（如閏四月 lunar_m=4），is_leap 被丟棄。
        # 原典凌犯月別表僅列正月至十二月，不含閏月獨立規則，
        # 故閏月以對應正月的朔日七曜代入，為最保守的 fallback。
        lunar_y, lunar_m, lunar_d, _ = self.solar_to_lunar(target_date)

        # 取得該農曆月朔日（初一）的西曆日期
        # 注：lunar_to_solar 固定 isleap=False，閏月時取正月初一的朔日七曜
        first_day_solar = self.lunar_to_solar(lunar_y, lunar_m, 1)
        if first_day_solar is None:
            return None

        # 朔日的七曜
        jp_weekday_first = (first_day_solar.weekday() + 1) % 7

        # 查表
        ryouhan = self.RYOUHAN_MAP.get((lunar_m, jp_weekday_first))
        if ryouhan is None:
            return None

        start_day, end_day = ryouhan

        # 判定當日農曆日是否在凌犯期間內
        if start_day <= lunar_d <= end_day:
            weekday_names = {0: "日曜", 1: "月曜", 2: "火曜", 3: "水曜", 4: "木曜", 5: "金曜", 6: "土曜"}
            wn = weekday_names[jp_weekday_first]
            month_desc = self.RYOUHAN_DESCRIPTIONS.get(lunar_m, {})

            return {
                "active": True,
                "reading": "りょうはんきかん",
                "lunar_month": lunar_m,
                "start_day": start_day,
                "end_day": end_day,
                "weekday_name": wn,
                "period_label": f"{lunar_m}月{wn}期",
                "description": month_desc.get("zh", f"農曆{lunar_m}月{start_day}日～{end_day}日為凌犯期間"),
                "description_ja": month_desc.get("ja", ""),
                "description_classic": month_desc.get("classic", ""),
                "source": "宿曜經品三・品五，及宿曜道傳承",
                "formula": {
                    "step1": f"西曆 {target_date} → 農曆 {lunar_y}/{lunar_m}/{lunar_d}",
                    "step2": f"農曆{lunar_m}月初一 = {first_day_solar}（{wn}）",
                    "step3": f"查表 RYOUHAN_MAP[({lunar_m}, {jp_weekday_first})] = ({start_day}, {end_day})",
                    "step4": f"農曆{lunar_d}日 {'在' if start_day <= lunar_d <= end_day else '不在'} [{start_day}, {end_day}] 區間"
                }
            }

        return None

    def get_rokugai_suku(self, birth_mansion_index: int) -> list[dict]:
        """
        計算六害宿

        凌犯期間中，以本命宿為基準，順時計方向計算 6 個大凶日宿。
        偏移量對應三九秘法中的特定位置（命/一九安/業/二九安/二九壊/三九栄）。

        Args:
            birth_mansion_index: 本命宿索引 (0-26)

        Returns:
            六害宿列表（含宿名、偏移、凶度）
        """
        results = []
        for name, info in self.ROKUGAI_OFFSETS.items():
            # 順時計 = 從本命宿往前數（加上偏移）
            target_index = (birth_mansion_index + info["offset"]) % 27
            target_mansion = self.mansions_data[target_index]
            results.append({
                "name": name,
                "name_reading": info["reading"],
                "mansion_index": target_index,
                "mansion_name": target_mansion["name_jp"],
                "mansion_reading": target_mansion["reading"],
                "severity": info["severity"],
                "offset": info["offset"]
            })
        # 按凶度排序（1=最凶）
        results.sort(key=lambda x: x["severity"])
        return results

    def get_sanki_cycle(self, birth_mansion_index: int, day_mansion_index: int, lang: str = 'zh-TW') -> dict:
        """
        計算日運三期サイクル

        27 日為一循環，從命宿開始依序分三期各 9 天：
        - 躍動の週（一九/活動期）：命宿起 9 天
        - 破壊の週（二九/衰退期）：業宿起 9 天
        - 再生の週（三九/轉換期）：胎宿起 9 天

        Args:
            birth_mansion_index: 本命宿索引
            day_mansion_index: 當日宿索引
            lang: 語系

        Returns:
            當日所屬的三期資訊
        """
        # 計算當日宿相對於命宿的距離（前向）
        distance = (day_mansion_index - birth_mansion_index) % 27

        # 分三期：0-8 = 躍動, 9-17 = 破壊, 18-26 = 再生
        period_index = distance // 9
        day_in_period = (distance % 9) + 1  # 第幾天（1-9）

        cycle_info = self.SANKI_CYCLE[period_index]

        # 暗黒の一週間：破壊の週 distance 9-15（業→栄→衰→安→危→成→壊）
        is_dark_week = (9 <= distance <= 15)

        # 日型判定：第 1 天為期起始日（命/業/胎），第 2-9 天為共通日型
        period_num = period_index + 1  # 1=一九, 2=二九, 3=三九
        if day_in_period == 1:
            day_type = self.SANKI_DAY_TYPES["period_start"][period_num]
        else:
            day_type = self.SANKI_DAY_TYPES["day"][day_in_period]

        # i18n: 從 sanki.json 讀取翻譯
        sanki_i18n = self._load_sanki_i18n(lang)
        i18n_day_types = sanki_i18n.get("day_types", {})
        i18n_period = sanki_i18n.get("period_descriptions", {})

        # 取得日型描述（i18n 優先）
        if day_in_period == 1:
            i18n_day_desc = i18n_day_types.get("period_start", {}).get(str(period_num))
        else:
            i18n_day_desc = i18n_day_types.get("day", {}).get(str(day_in_period))
        day_description = i18n_day_desc or day_type["description"]

        # 取得期描述（i18n 優先）
        i18n_period_desc = i18n_period.get(str(period_index))
        period_description = i18n_period_desc or cycle_info["description"]

        return {
            "period": cycle_info["name"],
            "period_reading": cycle_info["reading"],
            "period_index": period_num,
            "day_in_period": day_in_period,
            "is_dark_week": is_dark_week,
            "day_type": day_type["name"],
            "day_type_reading": day_type["reading"],
            "day_description": day_description,
            "day_description_ja": day_type.get("description_ja", ""),
            "period_description": period_description,
            "period_description_classic": cycle_info.get("description_classic", ""),
            "period_description_ja": cycle_info.get("description_ja", "")
        }

    def _analyze_compound_factors(
        self,
        ryouhan: dict | None,
        special_day_type: str | None,
        mansion_relation_type: str,
        sanki: dict,
        rokugai: dict | None
    ) -> list[dict]:
        """
        多因素交叉分析：偵測已知的因素疊加組合

        Returns:
            list[dict]，按 severity 降序排列。每個 dict 包含：
            pattern, severity, name, description, description_ja, description_classic
        """
        results = []
        is_dark_week = sanki.get("is_dark_week", False)
        is_auspicious_relation = mansion_relation_type in ("eishin", "mei")

        # 1. triple_auspicious：甘露/金剛 + 栄親/命（破壊の週的栄日/安日/成日仍可觸發）
        if special_day_type in ("kanro", "kongou") and is_auspicious_relation:
            if not ryouhan:
                results.append({
                    "pattern": "triple_auspicious",
                    "severity": 5,
                    "name": "三重大吉",
                    "description": "特殊吉日與大吉宿曜關係重疊，多重吉因加持之下，是難得的絕佳時機。把握今天推進重要事項。",
                    "description_ja": "特殊吉日と大吉の宿曜関係が重なり、三重の吉因が揃う極めて稀な好日。重要な事柄を進めるに最適。",
                    "description_classic": "（編者歸納）吉日吉宿相重，三因具足，百事大吉。"
                })

        # 2. ryouhan_trap：凌犯 + 栄親/命
        if ryouhan and is_auspicious_relation:
            results.append({
                "pattern": "ryouhan_trap",
                "severity": 5,
                "name": "凌犯陷阱",
                "description": "凌犯期間遇上表面大吉的宿曜關係，看似順遂實則暗藏風險。高分不代表安全，重大決策務必延後。",
                "description_ja": "凌犯期間中に大吉の宿曜関係が重なる「表吉実険」の配置。好調に見えても判断を誤りやすく、重要な決断は延期すべし。",
                "description_classic": "（編者歸納）凌犯中遇吉配，表吉實險。原典：「亦宜修福念善」（T21 p.391b-c）。"
            })

        # 3. ryouhan_kanro_reversed：凌犯 + 甘露日
        if ryouhan and special_day_type == "kanro":
            results.append({
                "pattern": "ryouhan_kanro_reversed",
                "severity": 4,
                "name": "甘露逆轉",
                "description": "本應是甘露大吉日，但凌犯期間使吉凶逆轉。原本的福澤被遮蔽，不宜以吉日心態行事。",
                "description_ja": "本来は甘露の大吉日なるも、凌犯期間により吉凶逆転。福徳が覆われ、吉日としての効力を失う。",
                "description_classic": "（編者歸納）甘露遇凌犯，吉凶逆轉。原典凌犯規則概括適用（T21 p.391b-c）。"
            })

        # 4. ryouhan_rokugai：凌犯 + 六害宿
        if ryouhan and rokugai:
            results.append({
                "pattern": "ryouhan_rokugai",
                "severity": 4,
                "name": "凌犯六害",
                "description": "凌犯期間又逢六害宿，雙重凶因疊加。今日需格外謹慎，避免重要行動，靜守為宜。",
                "description_ja": "凌犯期間中に六害宿が重なり、二重の凶因が作用する。格別の注意を要し、重要な行動を控え静かに過ごすべし。",
                "description_classic": "（編者歸納）凌犯六害相重。原典凌犯化解法：「宜修功德造善以禳之」（T21 p.392a-b，化解法參照凌犯規則，六害宿段無專屬化解記載）。"
            })

        # 5. compounded_negative：安壊 + 破壊の週の凶日型（業/衰/危/壊）
        sanki_day_type = sanki.get("day_type", "")
        dark_week_bad_days = ("業の日", "衰の日", "危の日", "壊の日")
        if mansion_relation_type == "ankai" and is_dark_week and sanki_day_type in dark_week_bad_days:
            results.append({
                "pattern": "compounded_negative",
                "severity": 4,
                "name": "凶因重疊",
                "description": "安壊的破壞性與破壊の週的凶日型重疊，運勢處於谷底。今天不是行動的日子，專注在不需要外界配合的事情上。",
                "description_ja": "安壊の破壊性と破壊の週の凶日型が重なり、運勢は最低点に。行動を控え、外部との関わりを最小限に留めるべし。",
                "description_classic": "（編者歸納）安壊逢破壊の凶日，凶因重疊。原典壊日：「餘並不堪」（T21 p.398a）。"
            })

        # 6. dark_rasetsu：羅刹日 + 暗黒の一週間
        if special_day_type == "rasetsu" and is_dark_week:
            if not ryouhan:  # 凌犯中羅刹已逆轉為吉，不算此組合
                results.append({
                    "pattern": "dark_rasetsu",
                    "severity": 3,
                    "name": "暗黒羅刹",
                    "description": "羅刹日的障礙加上暗黒の一週間的低迷，今天做什麼都容易卡住。放低期待，處理簡單的例行事務就好。",
                    "description_ja": "羅刹日の障碍と暗黒の一週間の低迷が重なる。何事も停滞しやすく、期待値を下げて日常の事務に専念すべし。",
                    "description_classic": "（編者歸納）羅刹逢暗黒，凶因重疊。原典：「不宜舉百事，必有殃禍」（T21 p.398c）。"
                })

        # 7. double_auspicious：金剛峯 + 栄親/命
        if special_day_type == "kongou" and is_auspicious_relation:
            if not ryouhan:  # 凌犯中已觸發 ryouhan_trap，不重複
                results.append({
                    "pattern": "double_auspicious",
                    "severity": 3,
                    "name": "雙重吉配",
                    "description": "金剛峯日的堅固守護加上大吉的宿曜關係，今天啟動的計畫特別容易持續下去。適合做需要長期堅持的決定。",
                    "description_ja": "金剛峯日の堅固なる守護と大吉の宿曜関係が重なる好配置。この日に始めたことは持続しやすく、長期的な決断に最適。",
                    "description_classic": "（編者歸納）金剛遇吉配，堅牢雙成。原典：「宜作一切降伏法…並諸猛利等事」（T21 p.398b-c）。"
                })

        # 按 severity 降序排列
        results.sort(key=lambda x: x["severity"], reverse=True)
        return results

    def get_special_days_for_month(self, year: int, month: int) -> list[dict]:
        """
        取得指定月份的所有特殊日（甘露日/金剛峯日/羅刹日）

        特殊日是全域的，由 (七曜, 當日宿) 決定，不需要個人生日。

        Args:
            year: 西曆年份
            month: 西曆月份 (1-12)

        Returns:
            特殊日列表
        """
        import calendar

        fortune_data = self._load_fortune_data()
        weekday_elements = fortune_data["weekday_elements"]

        days_in_month = calendar.monthrange(year, month)[1]
        results = []

        for day in range(1, days_in_month + 1):
            target_date = date(year, month, day)

            # 當日宿（修正後宿位）
            try:
                day_mansion_index = self._get_corrected_mansion_index(target_date)
            except Exception:
                continue
            day_mansion = self.mansions_data[day_mansion_index]

            # 七曜
            weekday = target_date.weekday()
            jp_weekday = (weekday + 1) % 7
            day_info = weekday_elements[str(jp_weekday)]

            # 查特殊日
            special_day_key = (jp_weekday, day_mansion_index)
            special_day_type = self.SPECIAL_DAY_MAP.get(special_day_key)

            if special_day_type:
                info = self.SPECIAL_DAY_INFO[special_day_type]
                # 凌犯期間判定
                ryouhan = self.check_ryouhan_period(target_date)
                level = info["level"]
                ryouhan_reversed = False
                if ryouhan:
                    if special_day_type in ("kanro", "kongou"):
                        level = "凶（凌犯逆轉）"
                        ryouhan_reversed = True
                    elif special_day_type == "rasetsu":
                        level = "吉（凌犯逆轉）"
                        ryouhan_reversed = True

                results.append({
                    "date": target_date.isoformat(),
                    "weekday": day_info["name"].replace("曜日", ""),
                    "type": special_day_type,
                    "name": info["name"],
                    "reading": info["reading"],
                    "level": level,
                    "mansion": day_mansion["name_jp"],
                    "mansion_reading": day_mansion["reading"],
                    "description": info["description"],
                    "description_classic": info.get("description_classic", ""),
                    "description_ja": info.get("description_ja", ""),
                    "ryouhan_reversed": ryouhan_reversed
                })

        return results

    def get_calendar_month(self, year: int, month: int, birth_date: Optional[date] = None, lang: str = 'zh-TW') -> dict:
        """
        取得整月的統合月曆資料

        整合宿位、七曜、凌犯期間、甘露/金剛峯/羅刹日，
        以及（有 birth_date 時的）三期サイクル、六害宿、簡化運勢分數。

        Args:
            year: 西曆年份
            month: 西曆月份 (1-12)
            birth_date: 出生日期（可選）

        Returns:
            統合月曆資料
        """
        import calendar as cal

        fortune_data = self._load_fortune_data()
        weekday_elements = fortune_data["weekday_elements"]

        days_in_month = cal.monthrange(year, month)[1]

        # 個人資料（若有 birth_date）
        user_index = None
        user_element = None
        user_mansion_info = None
        rokugai_indices = set()
        if birth_date:
            user_mansion = self.get_mansion(birth_date)
            user_index = user_mansion["index"]
            user_element = user_mansion["element"]
            user_mansion_info = {
                "name_jp": user_mansion["name_jp"],
                "reading": user_mansion["reading"],
                "element": user_element,
                "index": user_index,
            }
            # 預算六害宿索引（避免每日重算）
            for rg in self.get_rokugai_suku(user_index):
                rokugai_indices.add(rg["mansion_index"])

        days = []
        stats = {
            "ryouhan_days": 0,
            "kanro_count": 0,
            "kongou_count": 0,
            "rasetsu_count": 0,
        }

        for day_num in range(1, days_in_month + 1):
            target_date = date(year, month, day_num)

            # 當日宿（修正後宿位）
            try:
                day_mansion_index = self._get_corrected_mansion_index(target_date)
            except Exception:
                continue
            day_mansion = self.mansions_data[day_mansion_index]

            # 七曜
            weekday = target_date.weekday()
            jp_weekday = (weekday + 1) % 7
            day_info = weekday_elements[str(jp_weekday)]

            # 凌犯判定
            ryouhan = self.check_ryouhan_period(target_date)
            if ryouhan:
                stats["ryouhan_days"] += 1

            # 特殊日
            special_day_key = (jp_weekday, day_mansion_index)
            special_day_type = self.SPECIAL_DAY_MAP.get(special_day_key)
            special_day = None
            if special_day_type:
                info = self.SPECIAL_DAY_INFO[special_day_type]
                level = info["level"]
                ryouhan_reversed = False
                if ryouhan:
                    if special_day_type in ("kanro", "kongou"):
                        level = "凶（凌犯逆轉）"
                        ryouhan_reversed = True
                    elif special_day_type == "rasetsu":
                        level = "吉（凌犯逆轉）"
                        ryouhan_reversed = True
                special_day = {
                    "type": special_day_type,
                    "name": info["name"],
                    "level": level,
                    "ryouhan_reversed": ryouhan_reversed,
                }
                stats[f"{special_day_type}_count"] = stats.get(f"{special_day_type}_count", 0) + 1

            # 組裝每日資料
            day_entry = {
                "date": target_date.isoformat(),
                "day": day_num,
                "weekday": day_info["name"].replace("曜日", ""),
                "day_mansion": {
                    "name_jp": day_mansion["name_jp"],
                    "index": day_mansion_index,
                    "element": day_mansion["element"],
                },
                "special_day": special_day,
                "ryouhan": {"active": True, "lunar_month": ryouhan["lunar_month"]} if ryouhan else None,
            }

            # 個人化層（復用 _calc_daily_core 確保與運勢分數一致）
            if user_index is not None:
                core = self._calc_daily_core(user_index, user_element, target_date)

                # 六害宿（凌犯期間中才標記，不影響分數）
                rokugai = None
                if ryouhan and day_mansion_index in rokugai_indices:
                    rokugai = True

                day_entry["personal"] = {
                    "relation_type": core["relation"]["type"],
                    "relation_name": core["relation"]["name"],
                    "fortune_score": core["fortune_score"],
                    "level": core["final_level"],
                    "level_name": self._level_name(core["final_level"], lang),
                    "sanki_period": core["sanki"]["period"],
                    "sanki_period_index": core["sanki"]["period_index"],
                    "sanki_day_type": core["sanki"].get("day_type", ""),
                    "is_dark_week": core["sanki"]["is_dark_week"],
                    "rokugai": rokugai,
                }

            days.append(day_entry)

        result = {
            "year": year,
            "month": month,
            "days": days,
            "statistics": stats,
        }

        if user_mansion_info:
            result["personal"] = {"your_mansion": user_mansion_info}

        return result

    # ========================================================================
    # ICS 月曆產生（RFC 5545）
    # ========================================================================

    @staticmethod
    def _ics_escape(text: str) -> str:
        """跳脫 ICS 特殊字元"""
        return (
            text
            .replace('\\', '\\\\')
            .replace(';', '\\;')
            .replace(',', '\\,')
            .replace('\n', '\\n')
        )

    @staticmethod
    def _ics_fold_line(line: str) -> str:
        """RFC 5545 行摺疊：第一行 75 bytes，後續行 74 bytes（含前綴空格）"""
        encoded = line.encode('utf-8')
        if len(encoded) <= 75:
            return line

        parts: list[str] = []
        start = 0

        while start < len(line):
            max_bytes = 75 if start == 0 else 74
            end = start
            current_bytes = 0

            while end < len(line):
                char_bytes = len(line[end].encode('utf-8'))
                if current_bytes + char_bytes > max_bytes:
                    break
                current_bytes += char_bytes
                end += 1

            if end == start:
                # 單一字元超過限制（不應發生），強制推進
                end = start + 1

            parts.append(line[start:end])
            start = end

        return '\r\n '.join(parts)

    @staticmethod
    def _ics_format_date(d: date) -> str:
        """日期格式化為 ICS VALUE=DATE 格式（例: 20260115）"""
        return d.strftime('%Y%m%d')

    @staticmethod
    def _ics_fortune_level(score: int, level_name: str = "") -> str:
        """運勢分數轉等級名稱"""
        if level_name:
            return level_name
        if score >= 90:
            return '大吉'
        if score >= 75:
            return '吉'
        if score >= 60:
            return '中吉'
        if score >= 45:
            return '小凶'
        return '凶'

    @staticmethod
    def _ics_day_tip(level: str | None, personal: dict | None, day: dict) -> str:
        """白話提醒：依特殊日、凌犯、破壊の週、一般等級產生每日建議"""
        has_ryouhan = bool(day.get('ryouhan') and day['ryouhan'].get('active'))
        is_dark = bool(personal and personal.get('is_dark_week'))
        has_rokugai = bool(personal and personal.get('rokugai'))
        special_type = day['special_day']['type'] if day.get('special_day') else None
        reversed_ = bool(day.get('special_day') and day['special_day'].get('ryouhan_reversed'))

        # 特殊日優先
        if special_type == 'kanro' and not reversed_:
            return '甘露日：今天是難得的大吉日，適合開始新計畫、簽約、重要面談'
        if special_type == 'kanro' and reversed_:
            rokugai_suffix = '。又逢六害宿，宜修福：入灌頂及護摩，並修諸功德' if has_rokugai else ''
            return f'甘露日但在凌犯期間，吉凶逆轉。此時不宜因日名而草率行動，宜靜觀待時{rokugai_suffix}'
        if special_type == 'kongou' and not reversed_:
            return '金剛峯日：氣場強勢的一天，適合處理棘手的事、談判、護摩修法、下決心'
        if special_type == 'kongou' and reversed_:
            rokugai_suffix = '。又逢六害宿，宜修福：入灌頂及護摩，並修諸功德' if has_rokugai else ''
            return f'金剛峯日但在凌犯期間，吉凶逆轉。強勢能量易生阻力，宜靜觀待時{rokugai_suffix}'
        if special_type == 'rasetsu' and not reversed_:
            return '羅刹日：百事不宜，能延就延，今天不適合做重要決定'
        if special_type == 'rasetsu' and reversed_:
            rokugai_suffix = '。但逢六害宿，仍宜修福：入灌頂及護摩，並修諸功德' if has_rokugai else ''
            return f'羅刹日但凌犯逆轉，凶象減弱。保持平常心即可，無需過度擔憂{rokugai_suffix}'

        # 凌犯 + 六害宿（最需警戒）
        if has_ryouhan and has_rokugai:
            return '凌犯期間碰上六害宿，今天最該避開。原典記載宜修福：入灌頂及護摩，並修諸功德'

        # 破壊の週：依三九日型分別建議（原典各日吉凶不同）
        if is_dark:
            day_type = (personal or {}).get('sanki_day_type', '')
            if day_type == '栄の日':
                return '破壊の週但逢栄日，原典記載即宜入官拜職、對見大人、上書表進獻君王、興營買賣、裁著新衣、沐浴及諸吉事並大吉。可正常行動'
            if day_type == '安の日':
                return '破壊の週但逢安日，原典記載移徙吉，遠行人入宅、造作園宅、安坐臥床帳、作壇場並吉。穩定踏實的一天'
            if day_type == '成の日':
                return '破壊の週但逢成日，原典記載宜修道學問、合和長年藥法，作諸成就法並吉。適合修行精進'
            if day_type == '壊の日':
                return '破壊の週壊日，原典記載宜作鎮壓、降伏怨讎及討伐阻壞奸惡之謀，餘並不堪'
            if day_type == '業の日':
                return '破壊の週業日，原典記載所作善惡亦不成就，甚衰。低調收斂為上'
            if day_type == '衰の日':
                return '破壊の週衰日，原典記載唯宜解除諸惡、療病。保守度過'
            if day_type == '危の日':
                return '破壊の週危日，原典記載宜結交、定婚姻，歡宴聚會並吉。社交可行，重大決定宜避開'
            if day_type == '命の日':
                return '破壊の週命日，原典記載不宜舉動百事。低調靜養'
            if day_type == '胎の日':
                return '破壊の週胎日，原典記載不宜舉動百事。低調靜養'
            return '破壊の週，整體氣運偏弱，做好手邊的事就好'

        # 凌犯期間（無特殊日、無六害宿）
        if has_ryouhan:
            return '凌犯期間：吉凶可能相反，宜修福（入灌頂及護摩，並修諸功德），穩住心態'

        # 一般日按等級
        if level == '大吉':
            return '運勢很好的一天，想做什麼就行動吧，機會來了別猶豫'
        if level == '吉':
            return '不錯的一天，適合推進計畫、見重要的人'
        if level == '中吉':
            return '普通偏好，按部就班做事就行，不需要特別小心'
        if level == '小凶':
            return '稍微注意一下，別做太冒險的決定，穩穩來就沒問題'
        if level == '凶':
            return '運勢偏低，避開重大決策和衝突，今天適合休息充電'

        return '平穩的一天'

    def generate_ics_calendar(self, birth_date: date, year: int) -> str:
        """
        產生整年 ICS 月曆字串（RFC 5545）

        整合 12 個月的月曆資料，為每天產生一個全天事件，
        包含運勢等級、三期、特殊日標記及白話提醒。

        Args:
            birth_date: 出生日期
            year: 西曆年份

        Returns:
            RFC 5545 格式的 ICS 字串
        """
        from datetime import timedelta, datetime, timezone

        # 取得使用者本命宿資訊
        user_mansion = self.get_mansion(birth_date)
        mansion_name = user_mansion['name_jp']
        mansion_element = user_mansion['element']
        user_index = user_mansion['index']

        # DTSTAMP：產生時間（UTC）
        dtstamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')

        # VCALENDAR 標頭
        lines: list[str] = [
            'BEGIN:VCALENDAR',
            'VERSION:2.0',
            self._ics_fold_line(f'PRODID:-//Sukuyodo//Fortune Calendar//{year}//ZH'),
            'CALSCALE:GREGORIAN',
            'METHOD:PUBLISH',
            self._ics_fold_line(
                f'X-WR-CALNAME:{self._ics_escape(f"{mansion_name}({mansion_element}) {year} 年運勢")}'
            ),
            'X-WR-TIMEZONE:Asia/Taipei',
        ]

        # 逐月取得月曆資料
        event_index = 0
        for month in range(1, 13):
            cal_data = self.get_calendar_month(year, month, birth_date)

            for day in cal_data['days']:
                personal = day.get('personal')
                level = None
                if personal:
                    level = self._ics_fortune_level(
                        personal['fortune_score'],
                        personal.get('level_name', '')
                    )

                    # 補算 sanki_day_type（若 API 回傳已包含則跳過）
                    if 'sanki_day_type' not in personal or personal.get('sanki_day_type') is None:
                        day_mansion_index = day['day_mansion']['index']
                        sanki_info = self.get_sanki_cycle(user_index, day_mansion_index)
                        personal['sanki_day_type'] = sanki_info['day_type']

                # 標題：等級 | 三期縮寫 | 特殊標記
                title_segments: list[str] = []
                if level:
                    title_segments.append(level)
                if personal:
                    sanki_short = personal['sanki_period'].replace('の週', '')
                    title_segments.append(sanki_short)

                # 第三段：特殊標記
                markers: list[str] = []
                if day.get('special_day'):
                    reversed_tag = '(逆転)' if day['special_day'].get('ryouhan_reversed') else ''
                    markers.append(f"{day['special_day']['name']}{reversed_tag}")
                if day.get('ryouhan') and day['ryouhan'].get('active') and not day.get('special_day'):
                    markers.append('凌犯')
                if personal and personal.get('is_dark_week'):
                    markers.append('暗黒')
                if personal and personal.get('rokugai'):
                    markers.append('六害宿')
                if markers:
                    title_segments.append(' '.join(markers))

                summary = ' | '.join(title_segments)

                # 白話提醒
                tip = self._ics_day_tip(level, personal, day)

                # 描述（白話提醒 + 詳細資訊）
                desc_parts: list[str] = [tip, '---']
                if personal:
                    desc_parts.append(f"運勢: {personal['fortune_score']} ({level})")
                    desc_parts.append(f"關係: {personal['relation_name']}")
                    desc_parts.append(
                        f"宿: {day['day_mansion']['name_jp']}"
                        f"({day['day_mansion']['element']}) - {day['weekday']}"
                    )
                    desc_parts.append(f"三期: {personal['sanki_period']}")
                if day.get('special_day'):
                    sd = day['special_day']
                    if sd.get('ryouhan_reversed'):
                        sd_label = f"{sd['name']} (凌犯逆転: {sd['level']})"
                    else:
                        sd_label = f"{sd['name']} ({sd['level']})"
                    desc_parts.append(f"特殊日: {sd_label}")
                if day.get('ryouhan') and day['ryouhan'].get('active'):
                    desc_parts.append('-- 凌犯期間: 吉凶逆転に注意 --')
                if personal and personal.get('is_dark_week'):
                    day_type = personal.get('sanki_day_type', '')
                    desc_parts.append(f"-- 破壊の週 ({day_type or '二九'}) --")
                if personal and personal.get('rokugai'):
                    desc_parts.append('-- 六害宿 --')

                description = '\\n'.join(desc_parts)

                # 全天事件日期
                target_date = date.fromisoformat(day['date'])
                dt_start = self._ics_format_date(target_date)
                dt_end = self._ics_format_date(target_date + timedelta(days=1))

                # VEVENT
                uid = f"{day['date']}-{event_index}@sukuyodo"
                lines.append('BEGIN:VEVENT')
                lines.append(f'DTSTAMP:{dtstamp}')
                lines.append(self._ics_fold_line(f'UID:{uid}'))
                lines.append(f'DTSTART;VALUE=DATE:{dt_start}')
                lines.append(f'DTEND;VALUE=DATE:{dt_end}')
                lines.append(self._ics_fold_line(f'SUMMARY:{self._ics_escape(summary)}'))
                if description:
                    lines.append(self._ics_fold_line(f'DESCRIPTION:{description}'))
                lines.append('TRANSP:TRANSPARENT')
                lines.append('END:VEVENT')

                event_index += 1

        lines.append('END:VCALENDAR')

        return '\r\n'.join(lines)


# 全域實例
sukuyodo_service = SukuyodoService()
