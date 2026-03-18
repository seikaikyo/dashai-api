import os
from pathlib import Path
from anthropic import Anthropic, AsyncAnthropic
from typing import Optional
from dotenv import load_dotenv

from ..config.grammar_points import GRAMMAR_POINTS, LEVEL_LABELS, READING_LENGTH

# 載入專案根目錄的 .env 或系統環境變數
env_path = Path(__file__).parent.parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)

_client: Anthropic | None = None
_async_client: AsyncAnthropic | None = None


def get_system_prompt(mode: str, level: str, mastery_data: dict, weak_points: list[str]) -> str:
    """生成系統提示詞（依級別動態調整）"""

    level_label = LEVEL_LABELS.get(level, level.upper())
    grammar_points = GRAMMAR_POINTS.get(level, [])
    reading_config = READING_LENGTH.get(level, {})

    weak_points_str = '、'.join(weak_points) if weak_points else '尚未識別'
    mastery_summary = '\n'.join([
        f"- {k}: {v:.0%}" for k, v in mastery_data.items()
    ]) if mastery_data else '尚無數據'

    base_prompt = f"""你是專業的 JLPT {level_label} 日語教師，專精於文法和讀解教學。

## 用戶程度分析
- 目前級別：{level_label}
- 弱項領域：{weak_points_str}
- 目前練習模式：{mode}

## 掌握度數據
{mastery_summary}

## 教學原則
1. 全程使用正體中文說明（台灣用語）
2. 日文保持原文，重要詞彙標註假名
3. 解釋要清楚具體，避免模糊說法
4. 針對用戶弱項加強練習
5. 每次只出一題，等用戶回答後再繼續
6. 題目難度必須符合 {level.upper()} 級別
"""

    if mode == 'grammar':
        grammar_list = '、'.join(grammar_points[:10]) + '等'
        base_prompt += f"""

## 文法練習模式（{level.upper()} 考試題型）

模擬 JLPT {level.upper()} 的「言語知識（文法）」部分，出選擇題。

### 本級別文法範圍
{grammar_list}

### 題型
1. **文の組み立て**（句子重組）
2. **文法形式の判断**（選擇正確文法）

### 出題規則
- 每次出一題選擇題
- 提供 4 個選項（1/2/3/4）
- 題目要符合 {level.upper()} 程度
- 選項要有干擾性，不能太明顯

### 回覆格式

---
**問題 X**

＿＿＿に入る最も適切なものを選んでください。

（例句）

1. 選項一
2. 選項二
3. 選項三
4. 選項四

---

用戶回答後：
1. 告知正確答案
2. 簡短解釋為什麼（2-3 句話）
3. 說明該文法的用法重點
4. 問「繼續下一題？」

保持節奏明快，不要長篇大論。
"""
    elif mode == 'reading':
        lengths = ', '.join([
            f"{k}({v[0]}-{v[1]}字)" for k, v in reading_config.items()
        ])
        base_prompt += f"""

## 讀解練習模式（{level.upper()} 考試題型）

模擬 JLPT {level.upper()} 的「読解」部分，閱讀文章後回答選擇題。

### 文章長度
{lengths}

### 出題規則
- 先給一篇 {level.upper()} 程度的日文文章
- 文章主題：日常生活、社會議題、文化評論等
- 每篇文章出 1-3 題選擇題
- 問題類型：主旨理解、細節確認、作者意圖

### 回覆格式

---
**次の文章を読んで、後の問いに答えなさい。**

（日文文章）

---
**問1** 問題內容

1. ...
2. ...
3. ...
4. ...

---

用戶回答後：
1. 告知正確答案
2. 解釋為什麼這個選項正確
3. 說明其他選項為什麼不對（簡短）
4. 如果還有下一題就繼續，沒有就問「要換一篇新文章嗎？」

文章要有深度，選項要有干擾性，符合 {level.upper()} 真題難度。
"""
    elif mode == 'conversation':
        base_prompt += f"""

## 聽解練習模式（沉浸式體驗）

模擬 JLPT {level.upper()} 聽力測驗，讓用戶有「真的在聽」的感覺。

### 重要：使用 <dialogue> 標籤

對話內容必須用 `<dialogue>` 和 `</dialogue>` 標籤包起來，系統會自動朗讀這個區塊。
標籤外的內容（場景說明、問題、解說）不會被朗讀。

### 回覆格式

**場景設定**
（用中文描述場景，2-3 句話）

<dialogue>
A：對話內容...
B：對話內容...
</dialogue>

**質問**
問題內容

1. 選項一
2. 選項二
3. 選項三
4. 選項四

---

### 對話設計原則
- 對話複雜度符合 {level.upper()} 級別
- 語氣詞（えーと、あの、まあ）
- 省略和口語表達
- 不要在對話中加入動作描述

### 解答後
1. 告知正確答案
2. 引用對話中的關鍵線索（用中文解說）
3. 挑出一個自然日語表現解說
4. 「繼續下一題？」

情境：職場、學校、店舖、車站、醫院等日常場所。
"""

    return base_prompt


class ClaudeAPIError(Exception):
    """Claude API 呼叫失敗"""
    pass


def _get_client() -> Anthropic:
    """延遲初始化 Anthropic client"""
    global _client
    if _client is None:
        api_key = os.environ.get('ANTHROPIC_API_KEY')
        if not api_key:
            raise ClaudeAPIError('ANTHROPIC_API_KEY 未設定')
        _client = Anthropic(api_key=api_key)
    return _client


async def chat_with_claude(
    messages: list[dict],
    mode: str,
    level: str,
    mastery_data: dict,
    weak_points: list[str],
    api_key: str | None = None,
) -> str:
    """與 Claude 對話，失敗時拋出 ClaudeAPIError

    api_key: 用戶自訂的 API key（優先於 env）
    """
    system_prompt = get_system_prompt(mode, level, mastery_data, weak_points)

    try:
        active_client = Anthropic(api_key=api_key) if api_key else _get_client()
        response = active_client.messages.create(
            model='claude-sonnet-4-20250514',
            max_tokens=2048,
            system=system_prompt,
            messages=messages
        )
        return response.content[0].text
    except Exception as e:
        raise ClaudeAPIError(str(e)) from e


def _get_async_client(api_key: str | None = None) -> AsyncAnthropic:
    """取得 async client（用於串流）"""
    if api_key:
        return AsyncAnthropic(api_key=api_key)
    global _async_client
    if _async_client is None:
        key = os.environ.get('ANTHROPIC_API_KEY')
        if not key:
            raise ClaudeAPIError('ANTHROPIC_API_KEY 未設定')
        _async_client = AsyncAnthropic(api_key=key)
    return _async_client


async def stream_with_claude(
    messages: list[dict],
    mode: str,
    level: str,
    mastery_data: dict,
    weak_points: list[str],
    api_key: str | None = None,
):
    """與 Claude 串流對話，yield 文字片段"""
    system_prompt = get_system_prompt(mode, level, mastery_data, weak_points)

    try:
        client = _get_async_client(api_key)
        async with client.messages.stream(
            model='claude-sonnet-4-20250514',
            max_tokens=2048,
            system=system_prompt,
            messages=messages,
        ) as stream:
            async for text in stream.text_stream:
                yield text
    except Exception as e:
        raise ClaudeAPIError(str(e)) from e


def get_weak_grammar_points(mastery_data: dict, level: str = 'n1', threshold: float = 0.6) -> list[str]:
    """取得弱項文法點"""
    weak = [k for k, v in mastery_data.items() if v < threshold]

    grammar_points = GRAMMAR_POINTS.get(level, [])

    # 如果沒有數據，返回一些常考文法點
    if not weak and not mastery_data:
        return grammar_points[:5]

    return weak or grammar_points[:3]
