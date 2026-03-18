"""題庫服務

啟動時載入所有 JSON 到記憶體，提供加權選題、避免短期重複。
支援多級別 (N5-N1) 分層題庫。
"""

import json
import random
import logging
from pathlib import Path
from collections import defaultdict

from ..config.grammar_points import LEVELS

logger = logging.getLogger(__name__)

# 題庫根目錄
QUESTION_BANK_DIR = Path(__file__).parent.parent / 'data' / 'question_bank'

MODES = ('grammar', 'reading', 'conversation')


class QuestionBankService:
    """題庫載入與選題服務"""

    def __init__(self):
        # questions[level][mode] = [question_dict, ...]
        self._questions: dict[str, dict[str, list[dict]]] = {}
        self._used_ids: dict[str, set[str]] = defaultdict(set)
        self._last_question: dict[str, dict] = {}  # key: level_mode -> 最後出的題
        self._loaded = False

    def load(self):
        """載入所有題庫 JSON（按級別子目錄）"""
        if not QUESTION_BANK_DIR.exists():
            logger.warning('題庫目錄不存在: %s', QUESTION_BANK_DIR)
            return

        for level in LEVELS:
            self._questions[level] = {m: [] for m in MODES}
            level_dir = QUESTION_BANK_DIR / level
            if not level_dir.exists():
                continue

            for mode in MODES:
                mode_dir = level_dir / mode
                if not mode_dir.exists():
                    continue
                for f in mode_dir.glob('*.json'):
                    try:
                        data = json.loads(f.read_text(encoding='utf-8'))
                        if isinstance(data, list):
                            self._questions[level][mode].extend(data)
                        elif isinstance(data, dict) and 'questions' in data:
                            self._questions[level][mode].extend(data['questions'])
                    except (json.JSONDecodeError, KeyError) as e:
                        logger.error('載入題庫失敗 %s/%s/%s: %s', level, mode, f.name, e)

        self._loaded = True

        # 記錄各級別題目數
        for level in LEVELS:
            counts = {m: len(self._questions[level][m]) for m in MODES}
            total = sum(counts.values())
            if total > 0:
                logger.info(
                    '題庫 %s: grammar=%d, reading=%d, conversation=%d',
                    level.upper(), counts['grammar'], counts['reading'], counts['conversation'],
                )

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def total_questions(self) -> int:
        return sum(
            len(qs)
            for level_qs in self._questions.values()
            for qs in level_qs.values()
        )

    def has_questions(self, mode: str, level: str = 'n1') -> bool:
        return len(self._questions.get(level, {}).get(mode, [])) > 0

    def get_question(
        self,
        mode: str,
        level: str = 'n1',
        mastery_data: dict | None = None,
        weak_points: list[str] | None = None,
    ) -> dict | None:
        """取得一題

        加權選題邏輯（僅文法模式）：
        - 弱項文法權重 3x
        - 中等掌握 2x
        - 已熟練 1x
        """
        questions = self._questions.get(level, {}).get(mode, [])
        if not questions:
            return None

        # 用 level+mode 作為 used key，各級別分開追蹤
        used_key = f'{level}_{mode}'
        used = self._used_ids[used_key]
        available = [q for q in questions if q.get('id') not in used]

        # 全部用完就重置
        if not available:
            self._used_ids[used_key] = set()
            available = questions.copy()

        if mode == 'grammar' and mastery_data:
            selected = self._weighted_select_grammar(available, mastery_data)
        else:
            selected = random.choice(available)

        if selected and selected.get('id'):
            self._used_ids[used_key].add(selected['id'])

        # 記住最後出的題，供對答案用
        self._last_question[used_key] = selected

        return selected

    def check_answer(self, mode: str, level: str, user_answer: str) -> str | None:
        """對答案：回傳 answer_response 或 None"""
        used_key = f'{level}_{mode}'
        last_q = self._last_question.get(used_key)
        if not last_q:
            return None

        correct = last_q.get('correct_answer')
        answer_response = last_q.get('answer_response', '')

        # 判斷使用者答案是否正確
        try:
            user_num = int(user_answer.strip())
            if correct and user_num == correct:
                return f'{answer_response}'
            else:
                return f'不對喔！{answer_response}'
        except ValueError:
            # 非數字回答，直接回傳解答
            return answer_response

    def get_answer(self, question_id: str) -> dict | None:
        """根據 question_id 取得對應的解答回饋"""
        for level_qs in self._questions.values():
            for mode_questions in level_qs.values():
                for q in mode_questions:
                    if q.get('id') == question_id:
                        return q
        return None

    def _weighted_select_grammar(
        self, questions: list[dict], mastery_data: dict
    ) -> dict:
        """加權選題：弱項 3x，中等 2x，熟練 1x"""
        weights = []
        for q in questions:
            gp = q.get('grammar_point', '')
            clean_gp = gp.lstrip('〜').lstrip('~')
            mastery = None
            for k, v in mastery_data.items():
                if k.lstrip('〜').lstrip('~') == clean_gp:
                    mastery = v
                    break

            if mastery is None:
                weights.append(2)
            elif mastery < 0.4:
                weights.append(3)
            elif mastery < 0.7:
                weights.append(2)
            else:
                weights.append(1)

        return random.choices(questions, weights=weights, k=1)[0]

    def get_status(self) -> dict:
        """回傳題庫狀態"""
        counts_by_level = {}
        for level in LEVELS:
            level_qs = self._questions.get(level, {})
            level_counts = {m: len(level_qs.get(m, [])) for m in MODES}
            level_total = sum(level_counts.values())
            if level_total > 0:
                counts_by_level[level] = {**level_counts, 'total': level_total}

        return {
            'loaded': self._loaded,
            'levels': counts_by_level,
            'total': self.total_questions,
        }


# 全域單例
question_bank = QuestionBankService()
