"""題庫 + Fallback 服務

離線時轉為「結構化練習模式」：
- 文法填空
- 詞彙選擇 (4 選 1)
- 情境回應
- 發音練習

以及預建回應（keyword 匹配）。
"""

import json
import random
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / 'data' / 'question_bank'


class QuestionBankService:
    """英語題庫與 fallback 回應服務"""

    def __init__(self):
        self._drills: dict[str, list[dict]] = {
            'grammar_fill': [],
            'vocabulary': [],
            'situational': [],
            'pronunciation': [],
        }
        self._fallback_responses: dict[str, list[dict]] = {}
        self._used_drill_ids: set[str] = set()
        self._loaded = False

    def load(self):
        """載入所有題庫和預建回應"""
        # 載入練習題
        drills_dir = DATA_DIR / 'drills'
        if drills_dir.exists():
            for drill_type in self._drills:
                f = drills_dir / f'{drill_type}.json'
                if f.exists():
                    try:
                        data = json.loads(f.read_text(encoding='utf-8'))
                        if isinstance(data, list):
                            self._drills[drill_type] = data
                        elif isinstance(data, dict) and 'questions' in data:
                            self._drills[drill_type] = data['questions']
                    except (json.JSONDecodeError, KeyError) as e:
                        logger.error('載入 %s 失敗: %s', f.name, e)

        # 載入預建回應
        responses_dir = DATA_DIR / 'fallback_responses'
        if responses_dir.exists():
            for f in responses_dir.glob('*.json'):
                try:
                    data = json.loads(f.read_text(encoding='utf-8'))
                    scenario_name = f.stem  # 例如 interview-prep, free-chat
                    if isinstance(data, list):
                        self._fallback_responses[scenario_name] = data
                    elif isinstance(data, dict) and 'responses' in data:
                        self._fallback_responses[scenario_name] = data['responses']
                except (json.JSONDecodeError, KeyError) as e:
                    logger.error('載入 fallback 回應失敗 %s: %s', f.name, e)

        self._loaded = True
        drill_total = sum(len(d) for d in self._drills.values())
        resp_total = sum(len(r) for r in self._fallback_responses.values())
        logger.info(
            '題庫載入完成: drills=%d, fallback_responses=%d',
            drill_total, resp_total,
        )

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def detect_scenario(self, system_prompt: str) -> str | None:
        """從 system_prompt 偵測場景"""
        prompt_lower = system_prompt.lower()
        if 'interview' in prompt_lower or 'interviewer' in prompt_lower:
            return 'interview-prep'
        if 'free chat' in prompt_lower or 'conversation partner' in prompt_lower:
            return 'free-chat'
        return None

    def _find_fallback_entry(self, scenario: str, user_message: str) -> dict | None:
        """用 keyword 匹配預建回應，回傳完整 entry（含 response_zh）"""
        responses = self._fallback_responses.get(scenario, [])
        if not responses:
            return None

        msg_lower = user_message.lower().strip()

        for entry in responses:
            keywords = entry.get('keywords', [])
            if any(kw.lower() in msg_lower for kw in keywords):
                return entry

        return None

    def get_random_drill(self, want_translation: bool = False) -> str:
        """隨機取得一題練習題，格式化為回覆文字"""
        available_types = [t for t, qs in self._drills.items() if qs]
        if not available_types:
            return (
                "I'm currently in offline mode and don't have practice exercises available. "
                "Please try again later when the AI service is back online."
            )

        drill_type = random.choice(available_types)
        questions = self._drills[drill_type]

        # 過濾已出過的
        unused = [q for q in questions if q.get('id') not in self._used_drill_ids]
        if not unused:
            self._used_drill_ids = set()
            unused = questions.copy()

        question = random.choice(unused)
        if question.get('id'):
            self._used_drill_ids.add(question['id'])

        reply = question.get('response', self._format_drill(question, drill_type))
        if want_translation:
            return self._append_translation(reply, question.get('response_zh'))
        return reply

    def _format_drill(self, question: dict, drill_type: str) -> str:
        """格式化練習題為回覆文字"""
        if drill_type == 'grammar_fill':
            sentence = question.get('sentence', '')
            options = question.get('options', [])
            answer = question.get('answer', '')
            opts_text = '\n'.join(f'{i+1}. {o}' for i, o in enumerate(options))
            return (
                f"Let's practice grammar! Fill in the blank:\n\n"
                f"{sentence}\n\n{opts_text}\n\n"
                f"(The correct answer is: {answer})"
            )
        elif drill_type == 'vocabulary':
            prompt_text = question.get('prompt', '')
            options = question.get('options', [])
            answer = question.get('answer', '')
            opts_text = '\n'.join(f'{i+1}. {o}' for i, o in enumerate(options))
            return (
                f"Vocabulary check!\n\n{prompt_text}\n\n{opts_text}\n\n"
                f"(The correct answer is: {answer})"
            )
        elif drill_type == 'situational':
            situation = question.get('situation', '')
            example = question.get('example_response', '')
            return (
                f"Situational response practice:\n\n"
                f"Situation: {situation}\n\n"
                f"How would you respond?\n\n"
                f"Example answer: {example}"
            )
        elif drill_type == 'pronunciation':
            word = question.get('word', '')
            tip = question.get('tip', '')
            return (
                f"Pronunciation practice:\n\n"
                f"Word: {word}\n\n"
                f"Tip: {tip}"
            )
        return question.get('response', 'Practice question not available.')

    def _has_translation_mode(self, system_prompt: str) -> bool:
        """檢查是否啟用翻譯模式"""
        return '---TRANSLATION_MODE---' in system_prompt

    def _append_translation(self, response: str, translation: str | None) -> str:
        """如有翻譯則附加 ---TRANSLATION--- 區塊"""
        if translation:
            return f"{response}\n\n---TRANSLATION---\n\n{translation}"
        return response

    def get_fallback_reply(self, system_prompt: str, user_message: str) -> str:
        """取得 fallback 回覆（主要入口）

        1. 偵測場景
        2. keyword 匹配預建回應
        3. 都沒匹配 → 出一般練習題
        """
        want_translation = self._has_translation_mode(system_prompt)
        scenario = self.detect_scenario(system_prompt)

        if scenario:
            matched = self._find_fallback_entry(scenario, user_message)
            if matched:
                reply = matched.get('response', '')
                if want_translation:
                    return self._append_translation(reply, matched.get('response_zh'))
                return reply

        return self.get_random_drill(want_translation)

    def get_status(self) -> dict:
        """回傳題庫狀態"""
        return {
            'loaded': self._loaded,
            'drills': {
                dtype: len(questions)
                for dtype, questions in self._drills.items()
            },
            'fallback_responses': {
                scenario: len(responses)
                for scenario, responses in self._fallback_responses.items()
            },
            'total_drills': sum(len(d) for d in self._drills.values()),
            'total_responses': sum(len(r) for r in self._fallback_responses.values()),
        }


# 全域單例
question_bank = QuestionBankService()
