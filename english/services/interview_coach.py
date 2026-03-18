import json
import logging

import anthropic

logger = logging.getLogger(__name__)


def analyze_interview_answer(
    client: anthropic.Anthropic,
    model: str,
    question_id: str,
    user_answer: str,
    sample_answer: str,
    key_points: list[str],
) -> dict:
    """使用 Claude 分析面試回答"""

    system_prompt = """你是一位專業的英文面試教練。分析使用者的面試回答，提供具體、有建設性的回饋。
回饋必須使用繁體中文（台灣用語）。

請以 JSON 格式回覆，包含以下欄位：
- grammar_errors: 文法錯誤列表，每個包含 original（原文）、corrected（修正）、explanation（繁中說明）
- missed_points: 使用者遺漏的重點（繁中）
- fluency_score: 流暢度評分 1-10
- suggestions: 改善建議列表（繁中）
- encouragement: 一句鼓勵的話（繁中）

只回傳 JSON，不要其他文字。"""

    user_prompt = f"""面試問題 ID: {question_id}

使用者的回答:
{user_answer}

範本回答（參考用）:
{sample_answer}

應涵蓋的重點:
{', '.join(key_points)}

請分析使用者的回答並提供回饋。"""

    try:
        resp = client.messages.create(
            model=model,
            max_tokens=1000,
            system=system_prompt,
            messages=[{'role': 'user', 'content': user_prompt}],
        )

        text = resp.content[0].text.strip()

        # 嘗試解析 JSON（處理 markdown code block）
        if text.startswith('```'):
            text = text.split('\n', 1)[1] if '\n' in text else text[3:]
            text = text.rsplit('```', 1)[0]
            text = text.strip()

        return json.loads(text)

    except json.JSONDecodeError:
        logger.warning('Claude 回傳非 JSON 格式: %s', text[:200] if text else 'empty')
        return {
            'grammar_errors': [],
            'missed_points': [],
            'fluency_score': 5,
            'suggestions': ['AI 分析格式異常，請參考離線回饋。'],
            'encouragement': '繼續練習！',
        }
    except Exception as e:
        logger.error('面試分析失敗: %s', e)
        raise
