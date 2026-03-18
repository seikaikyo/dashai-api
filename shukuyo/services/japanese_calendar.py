"""日本選日曆注服務 - 傳統擇日系統"""
from datetime import date, timedelta
from typing import Literal


class JapaneseCalendarService:
    """
    日本選日曆注服務

    實作日本傳統的選日系統，包含：
    - 一粒萬倍日（いちりゅうまんばいび）
    - 天赦日（てんしゃにち/てんしゃび）
    - 寅の日（とらのひ）
    - 巳の日（みのひ）
    - 不成就日（ふじょうじゅび）
    - 六曜（ろくよう）
    """

    # 天干（十干）
    STEMS = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
    STEMS_READING = ["きのえ", "きのと", "ひのえ", "ひのと", "つちのえ",
                     "つちのと", "かのえ", "かのと", "みずのえ", "みずのと"]

    # 地支（十二支）
    BRANCHES = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
    BRANCHES_READING = ["ね", "うし", "とら", "う", "たつ", "み",
                        "うま", "ひつじ", "さる", "とり", "いぬ", "い"]
    BRANCHES_ANIMAL = ["鼠", "牛", "虎", "兔", "龍", "蛇", "馬", "羊", "猴", "雞", "狗", "豬"]

    # 六曜順序
    ROKUYO = ["大安", "赤口", "先勝", "友引", "先負", "仏滅"]
    ROKUYO_READING = ["たいあん", "しゃっこう", "せんしょう", "ともびき", "せんぶ", "ぶつめつ"]
    ROKUYO_MEANING = [
        "終日吉、万事大吉",           # 大安
        "正午前後一時吉、他凶",       # 赤口
        "午前吉、午後凶",             # 先勝
        "朝夕吉、正午凶",             # 友引
        "午前凶、午後吉",             # 先負
        "終日凶、慶事避ける",         # 仏滅
    ]

    # 一粒萬倍日：每月對應的地支
    # 格式：{月份: [地支索引列表]}
    ICHIRYUMANBAI_MAP = {
        1: [1, 6],    # 丑、午
        2: [9, 2],    # 酉、寅
        3: [0, 3],    # 子、卯
        4: [3, 4],    # 卯、辰
        5: [5, 6],    # 巳、午
        6: [6, 9],    # 午、酉
        7: [0, 7],    # 子、未
        8: [3, 8],    # 卯、申
        9: [6, 9],    # 午、酉
        10: [9, 10],  # 酉、戌
        11: [0, 11],  # 子、亥
        12: [0, 3],   # 子、卯
    }

    # 天赦日：季節對應的干支組合
    # 春(2-4月)=戊寅, 夏(5-7月)=甲午, 秋(8-10月)=戊申, 冬(11-1月)=甲子
    TENSYA_MAP = {
        "spring": (4, 2),   # 戊寅 (stem=4, branch=2)
        "summer": (0, 6),   # 甲午 (stem=0, branch=6)
        "autumn": (4, 8),   # 戊申 (stem=4, branch=8)
        "winter": (0, 0),   # 甲子 (stem=0, branch=0)
    }

    # 節月境界：(西曆月, 近似節氣日, 對應節月)
    # 用於一粒萬倍日等需要節月的計算
    SETSU_BOUNDARIES = [
        (1, 6, 12),   # 小寒 → 節月12
        (2, 4, 1),    # 立春 → 節月1
        (3, 6, 2),    # 驚蟄 → 節月2
        (4, 5, 3),    # 清明 → 節月3
        (5, 6, 4),    # 立夏 → 節月4
        (6, 6, 5),    # 芒種 → 節月5
        (7, 7, 6),    # 小暑 → 節月6
        (8, 7, 7),    # 立秋 → 節月7
        (9, 8, 8),    # 白露 → 節月8
        (10, 8, 9),   # 寒露 → 節月9
        (11, 7, 10),  # 立冬 → 節月10
        (12, 7, 11),  # 大雪 → 節月11
    ]

    # 不成就日：每月的特定日期
    # 日本不成就日每月有固定的日期模式
    FUJOUBYOU_PATTERN = {
        1: [3, 11, 19, 27],
        2: [2, 10, 18, 26],
        3: [1, 9, 17, 25],
        4: [4, 12, 20, 28],
        5: [5, 13, 21, 29],
        6: [6, 14, 22, 30],
        7: [3, 11, 19, 27],
        8: [2, 10, 18, 26],
        9: [1, 9, 17, 25],
        10: [4, 12, 20, 28],
        11: [5, 13, 21, 29],
        12: [6, 14, 22, 30],
    }

    # 各類吉日/凶日的說明
    DAY_TYPE_DESCRIPTIONS = {
        "tensya": {
            "name": "天赦日",
            "reading": "てんしゃにち",
            "short": "年間最大吉日",
            "description": "一年之中最吉祥的日子，日文寫作「天が万物の罪を赦す日」，意為天赦萬物之罪。一年大約只有五到六天，適合開始任何新事物、做重大決定、處理過去遺留的問題。如果跟一粒萬倍日重疊，被稱為最強開運日。"
        },
        "ichiryumanbai": {
            "name": "一粒萬倍日",
            "reading": "いちりゅうまんばいび",
            "short": "開始新事物吉",
            "description": "字面意思是「一粒種子可收穫萬倍」。在這天開始的事情、投入的金錢、建立的關係，都有可能以倍數的方式成長回報。適合開業、存錢、學習、種植等「播種型」的行動。但反過來說，這天借錢或開始壞習慣也會加倍放大，需要注意。每月約有四到六天。"
        },
        "tora_no_hi": {
            "name": "寅の日",
            "reading": "とらのひ",
            "short": "財運、旅行吉",
            "description": "寅（虎）是毘沙門天的使者，毘沙門天掌管財運和武運。虎有「千里行って千里帰る」（千里來回）的說法，代表出去的錢會回來。適合投資理財、開始新的收入來源、出差旅行。每十二天出現一次。不適合婚禮（虎會把新娘帶回娘家的迷信）。"
        },
        "mi_no_hi": {
            "name": "巳の日",
            "reading": "みのひ",
            "short": "金運、藝術吉",
            "description": "巳（蛇）是弁財天的使者，弁財天掌管財運、藝術和智慧。每十二天出現一次。這天適合存錢到弁財天相關的銀行帳戶、購買彩券、開始藝術創作、求取才藝方面的進步。"
        },
        "tsuchinoto_mi": {
            "name": "己巳の日",
            "reading": "つちのとみのひ",
            "short": "最強金運日",
            "description": "己巳之日是巳の日之中特別吉祥的版本，被認為是最強的金運日。六十天才出現一次。除了巳の日的所有好處之外，己巳日的財運加成更強。很多人會在這天開新的存款帳戶或錢包。"
        },
        "fujoubyou": {
            "name": "不成就日",
            "reading": "ふじょうじゅび",
            "short": "萬事不成之日",
            "description": "日文寫作「何事も成就しない日」，意為這天開始的任何事情都不容易有結果。應避免開業、簽約、結婚、搬家等重大決定。如果跟一粒萬倍日或天赦日重疊，吉凶相消，效果會打折。每月約有四天。"
        }
    }

    def __init__(self):
        pass

    def get_stem_branch(self, target_date: date) -> tuple[int, int]:
        """
        計算日干支

        使用 1900-01-01 為甲子日 (0, 0) 作為基準

        Args:
            target_date: 目標日期

        Returns:
            (天干索引, 地支索引)
        """
        # 1900-01-01 是甲戌日（天干=甲(0)，地支=戌(10)）
        base = date(1900, 1, 1)
        days = (target_date - base).days
        stem = days % 10
        branch = (days + 10) % 12
        return stem, branch

    def get_stem_branch_name(self, target_date: date) -> dict:
        """
        取得日干支的完整資訊

        Args:
            target_date: 目標日期

        Returns:
            包含干支名稱、讀音的字典
        """
        stem, branch = self.get_stem_branch(target_date)
        return {
            "stem": self.STEMS[stem],
            "stem_reading": self.STEMS_READING[stem],
            "branch": self.BRANCHES[branch],
            "branch_reading": self.BRANCHES_READING[branch],
            "animal": self.BRANCHES_ANIMAL[branch],
            "full": f"{self.STEMS[stem]}{self.BRANCHES[branch]}",
            "stem_index": stem,
            "branch_index": branch
        }

    def get_season(self, target_date: date) -> Literal["spring", "summer", "autumn", "winter"]:
        """
        根據月份判定季節

        日本傳統曆法的季節劃分：
        - 春：2月、3月、4月
        - 夏：5月、6月、7月
        - 秋：8月、9月、10月
        - 冬：11月、12月、1月

        Args:
            target_date: 目標日期

        Returns:
            季節名稱
        """
        month = target_date.month
        if month in [2, 3, 4]:
            return "spring"
        elif month in [5, 6, 7]:
            return "summer"
        elif month in [8, 9, 10]:
            return "autumn"
        else:
            return "winter"

    def get_setsugetsu(self, target_date: date) -> int:
        """
        取得節月（二十四節氣劃分的月份）

        節月以節氣為分界，與西曆月不同：
        - 立春(約2/4)起為節月1，驚蟄(約3/6)起為節月2，以此類推
        - 大雪(約12/7)起為節月11，小寒(約1/6)起為節月12

        Args:
            target_date: 目標日期

        Returns:
            節月 (1-12)
        """
        m = target_date.month
        d = target_date.day

        # 找出當月的節氣日，判定屬於哪個節月
        for solar_month, setsu_day, setsu_month in self.SETSU_BOUNDARIES:
            if m == solar_month:
                if d >= setsu_day:
                    return setsu_month
                # 日期在節氣之前，屬於前一個節月
                prev_idx = (self.SETSU_BOUNDARIES.index((solar_month, setsu_day, setsu_month)) - 1) % 12
                return self.SETSU_BOUNDARIES[prev_idx][2]

        return m  # fallback

    def is_ichiryumanbai(self, target_date: date) -> bool:
        """
        判定是否為一粒萬倍日

        一粒萬倍日意為「一粒種子可收穫萬倍」，
        適合開業、投資、求財等開始新事物的日子。

        Args:
            target_date: 目標日期

        Returns:
            是否為一粒萬倍日
        """
        _, branch = self.get_stem_branch(target_date)
        valid_branches = self.ICHIRYUMANBAI_MAP.get(self.get_setsugetsu(target_date), [])
        return branch in valid_branches

    def is_tensya(self, target_date: date) -> bool:
        """
        判定是否為天赦日

        天赦日是一年中最吉祥的日子，
        「天が万物の罪を赦す日」（天赦萬物之罪的日子）。
        一年約有 5-6 天。

        Args:
            target_date: 目標日期

        Returns:
            是否為天赦日
        """
        stem, branch = self.get_stem_branch(target_date)
        season = self.get_season(target_date)
        required = self.TENSYA_MAP[season]
        return (stem, branch) == required

    def is_tora_no_hi(self, target_date: date) -> bool:
        """
        判定是否為寅の日

        寅（虎）被視為財運之神毘沙門天的使者，
        適合求財、開運、旅行出發。
        每 12 天一次。

        Args:
            target_date: 目標日期

        Returns:
            是否為寅の日
        """
        _, branch = self.get_stem_branch(target_date)
        return branch == 2  # 寅

    def is_mi_no_hi(self, target_date: date) -> bool:
        """
        判定是否為巳の日

        巳（蛇）被視為弁財天的使者，
        適合財運、藝術、才能相關的祈願。
        每 12 天一次。

        Args:
            target_date: 目標日期

        Returns:
            是否為巳の日
        """
        _, branch = self.get_stem_branch(target_date)
        return branch == 5  # 巳

    def is_tsuchinoto_mi(self, target_date: date) -> bool:
        """
        判定是否為己巳の日（つちのとみのひ）

        己巳之日是巳の日中特別吉祥的日子，
        被認為是最強的金運日。
        每 60 天一次。

        Args:
            target_date: 目標日期

        Returns:
            是否為己巳の日
        """
        stem, branch = self.get_stem_branch(target_date)
        return stem == 5 and branch == 5  # 己巳

    def is_fujoubyou(self, target_date: date) -> bool:
        """
        判定是否為不成就日

        不成就日意為「何事も成就しない日」（萬事不成之日），
        應避免開始新事物、簽約、結婚等重要事項。

        Args:
            target_date: 目標日期

        Returns:
            是否為不成就日
        """
        try:
            from lunarcalendar import Converter, Solar
            solar = Solar(target_date.year, target_date.month, target_date.day)
            lunar = Converter.Solar2Lunar(solar)
            pattern = self.FUJOUBYOU_PATTERN.get(lunar.month, [])
            return lunar.day in pattern
        except ImportError:
            pattern = self.FUJOUBYOU_PATTERN.get(target_date.month, [])
            return target_date.day in pattern

    def get_rokuyo(self, target_date: date) -> dict:
        """
        計算六曜

        六曜是日本最常用的曆注之一，
        依序為：先勝、友引、先負、仏滅、大安、赤口

        計算方式：(農曆月 + 農曆日) mod 6

        Args:
            target_date: 目標日期

        Returns:
            六曜資訊
        """
        # 使用農曆月日計算：(農曆月 + 農曆日) mod 6
        try:
            from lunarcalendar import Converter, Solar
            solar = Solar(target_date.year, target_date.month, target_date.day)
            lunar = Converter.Solar2Lunar(solar)
            idx = (lunar.month + lunar.day) % 6
        except ImportError:
            # lunarcalendar 未安裝時用西曆近似
            idx = (target_date.month + target_date.day) % 6
        return {
            "name": self.ROKUYO[idx],
            "reading": self.ROKUYO_READING[idx],
            "meaning": self.ROKUYO_MEANING[idx],
            "index": idx
        }

    def get_day_info(self, target_date: date) -> dict:
        """
        取得單日的完整選日資訊

        Args:
            target_date: 目標日期

        Returns:
            包含所有選日資訊的字典
        """
        # 計算各種吉日
        is_ichiryu = self.is_ichiryumanbai(target_date)
        is_ten = self.is_tensya(target_date)
        is_tora = self.is_tora_no_hi(target_date)
        is_mi = self.is_mi_no_hi(target_date)
        is_tsuchi_mi = self.is_tsuchinoto_mi(target_date)
        is_fujo = self.is_fujoubyou(target_date)

        # 收集類型和標籤
        types = []
        labels = []
        descriptions = []

        if is_ten:
            types.append("tensya")
            labels.append("天赦日")
            descriptions.append(self.DAY_TYPE_DESCRIPTIONS["tensya"]["description"])
        if is_ichiryu:
            types.append("ichiryumanbai")
            labels.append("一粒萬倍日")
            descriptions.append(self.DAY_TYPE_DESCRIPTIONS["ichiryumanbai"]["description"])
        if is_tsuchi_mi:
            types.append("tsuchinoto_mi")
            labels.append("己巳の日")
            descriptions.append(self.DAY_TYPE_DESCRIPTIONS["tsuchinoto_mi"]["description"])
        elif is_mi:
            types.append("mi_no_hi")
            labels.append("巳の日")
            descriptions.append(self.DAY_TYPE_DESCRIPTIONS["mi_no_hi"]["description"])
        if is_tora:
            types.append("tora_no_hi")
            labels.append("寅の日")
            descriptions.append(self.DAY_TYPE_DESCRIPTIONS["tora_no_hi"]["description"])

        # 判斷是否為超吉日（多重吉日重疊）
        lucky_count = len(types)
        is_super_lucky = lucky_count >= 2

        # 取得干支和六曜
        stem_branch = self.get_stem_branch_name(target_date)
        rokuyo = self.get_rokuyo(target_date)

        # 星期幾
        weekday_names = ["月曜日", "火曜日", "水曜日", "木曜日", "金曜日", "土曜日", "日曜日"]
        weekday = weekday_names[target_date.weekday()]

        return {
            "date": target_date.isoformat(),
            "weekday": weekday,
            "stem_branch": stem_branch,
            "rokuyo": rokuyo,
            "types": types,
            "labels": labels,
            "descriptions": descriptions,
            "is_super_lucky": is_super_lucky,
            "is_fujoubyou": is_fujo,
            "fujoubyou_description": self.DAY_TYPE_DESCRIPTIONS["fujoubyou"]["description"] if is_fujo else None
        }

    def get_calendar_days(self, year: int, month: int) -> dict:
        """
        取得整月的選日資訊

        Args:
            year: 年份
            month: 月份 (1-12)

        Returns:
            包含吉日列表和凶日列表的字典
        """
        # 計算該月有多少天
        if month == 12:
            next_month = date(year + 1, 1, 1)
        else:
            next_month = date(year, month + 1, 1)
        first_day = date(year, month, 1)
        days_in_month = (next_month - first_day).days

        lucky_days = []
        unlucky_days = []

        for day in range(1, days_in_month + 1):
            target_date = date(year, month, day)
            day_info = self.get_day_info(target_date)

            # 有吉日類型的加入 lucky_days
            if day_info["types"]:
                lucky_days.append({
                    "date": day_info["date"],
                    "weekday": day_info["weekday"],
                    "types": day_info["types"],
                    "labels": day_info["labels"],
                    "descriptions": day_info["descriptions"],
                    "is_super_lucky": day_info["is_super_lucky"],
                    "stem_branch": day_info["stem_branch"]["full"],
                    "rokuyo": day_info["rokuyo"]["name"]
                })

            # 不成就日加入 unlucky_days
            if day_info["is_fujoubyou"]:
                unlucky_days.append({
                    "date": day_info["date"],
                    "weekday": day_info["weekday"],
                    "type": "fujoubyou",
                    "label": "不成就日",
                    "stem_branch": day_info["stem_branch"]["full"],
                    "rokuyo": day_info["rokuyo"]["name"]
                })

        return {
            "year": year,
            "month": month,
            "days": lucky_days,
            "unlucky_days": unlucky_days,
            "summary": {
                "tensya_count": sum(1 for d in lucky_days if "tensya" in d["types"]),
                "ichiryumanbai_count": sum(1 for d in lucky_days if "ichiryumanbai" in d["types"]),
                "tora_count": sum(1 for d in lucky_days if "tora_no_hi" in d["types"]),
                "mi_count": sum(1 for d in lucky_days if "mi_no_hi" in d["types"] or "tsuchinoto_mi" in d["types"]),
                "super_lucky_count": sum(1 for d in lucky_days if d["is_super_lucky"]),
                "fujoubyou_count": len(unlucky_days)
            }
        }

    def get_day_type_descriptions(self) -> dict:
        """取得所有吉日/凶日類型的說明"""
        return self.DAY_TYPE_DESCRIPTIONS


# 全域實例
japanese_calendar_service = JapaneseCalendarService()
