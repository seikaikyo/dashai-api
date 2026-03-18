"""
TTS 文字解析服務
將 Claude 回應解析成適合語音朗讀的格式
"""
import re
from typing import Optional


class TTSSegment:
    """TTS 片段"""
    def __init__(
        self,
        text: str,
        speaker: Optional[str] = None,
        lang: str = 'ja',
        pause_after: str = 'none'  # none, short, long, speaker
    ):
        self.text = text
        self.speaker = speaker
        self.lang = lang
        self.pause_after = pause_after

    def to_dict(self) -> dict:
        return {
            'text': self.text,
            'speaker': self.speaker,
            'lang': self.lang,
            'pause_after': self.pause_after
        }


def is_japanese(text: str) -> bool:
    """檢查文字是否為日文（聽解模式下預設為日文）"""
    for char in text:
        code = ord(char)
        # 平假名: 3040-309F, 片假名: 30A0-30FF
        if (0x3040 <= code <= 0x309F) or (0x30A0 <= code <= 0x30FF):
            return True
    # 純漢字也可能是日文，檢查是否有中文特有字符
    # 如果沒有明顯中文標記，預設當日文處理
    return False


def is_chinese(text: str) -> bool:
    """檢查文字是否為中文（有中文標點或常用中文詞）"""
    # 中文標點
    chinese_punctuation = '，。！？、；：「」『』【】'
    for char in text:
        if char in chinese_punctuation:
            return True
    # 常見中文詞（台灣用語）
    chinese_markers = ['的', '是', '在', '了', '嗎', '呢', '啊', '吧', '喔', '欸', '這', '那', '什麼', '怎麼', '為什麼']
    for marker in chinese_markers:
        if marker in text:
            return True
    return False


def clean_for_tts(text: str) -> str:
    """清理文字，只保留可朗讀的內容"""
    # 移除 markdown 格式
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'#{1,6}\s*', '', text)
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    text = re.sub(r'```[\s\S]*?```', '', text)

    # 移除分隔線
    text = re.sub(r'^---+\s*$', '', text, flags=re.MULTILINE)

    # 移除 emoji 和特殊符號
    text = re.sub(r'[🎧🔊❓✓✗📝💡🎯📌⭐️]', '', text)

    # 移除括號內的動作描述
    text = re.sub(r'（[^）]*）', '', text)
    text = re.sub(r'\([^)]*\)', '', text)

    return text.strip()


def clean_segment_text(text: str) -> str:
    """清理單個片段的文字，只保留可朗讀字符"""
    if not text:
        return ''

    # 只保留：平假名、片假名、漢字、空格、數字
    # 平假名: 3040-309F, 片假名: 30A0-30FF, 漢字: 4E00-9FFF, 3400-4DBF
    result = []
    for char in text:
        code = ord(char)
        if ((0x3040 <= code <= 0x309F) or  # 平假名
            (0x30A0 <= code <= 0x30FF) or  # 片假名
            (0x4E00 <= code <= 0x9FFF) or  # 漢字
            (0x3400 <= code <= 0x4DBF) or  # 漢字擴充
            char.isspace() or              # 空格
            char.isdigit()):               # 數字
            result.append(char)
        else:
            result.append(' ')

    return ' '.join(''.join(result).split())


def split_by_punctuation(text: str) -> list[tuple[str, str]]:
    """
    按標點分割文字，回傳 (文字, 停頓類型) 列表
    停頓類型: none, short (逗號), long (句號)
    """
    if not text:
        return []

    result = []

    # 逗號類（短停頓）
    short_pause = r'[、，,]'
    # 句號類（長停頓）
    long_pause = r'[。．.！？!?]'

    # 先按句號類分割
    sentences = re.split(f'({long_pause})', text)

    for i, part in enumerate(sentences):
        if not part or re.match(long_pause, part):
            continue

        # 再按逗號類分割
        clauses = re.split(f'({short_pause})', part)

        for j, clause in enumerate(clauses):
            if not clause or re.match(short_pause, clause):
                continue

            clause = clause.strip()
            if not clause:
                continue

            # 決定停頓類型
            pause = 'none'

            # 如果下一個是逗號
            if j + 1 < len(clauses) and re.match(short_pause, clauses[j + 1] or ''):
                pause = 'short'

            # 如果這是句子最後一個子句，且後面是句號
            is_last_clause = (j >= len(clauses) - 2)
            if is_last_clause and i + 1 < len(sentences):
                next_part = sentences[i + 1] if i + 1 < len(sentences) else ''
                if re.match(long_pause, next_part or ''):
                    pause = 'long'

            result.append((clause, pause))

    return result


def parse_dialogue(text: str) -> list[dict]:
    """
    解析對話格式，回傳說話者和內容
    格式: 山田：内容 或 山田: 内容
    """
    segments = []
    lines = text.split('\n')

    # 記錄說話者順序，用來分配性別（交替男女）
    speaker_order = []

    # 對話 pattern: 名字（最多15字）+ 冒號 + 內容
    dialogue_pattern = re.compile(r'^([^：:\n]{1,15})[：:](.+)$')

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 跳過 markdown、標題、分隔線、選項
        if (line.startswith('#') or
            line.startswith('---') or
            line.startswith('**') or
            line.startswith('http') or
            re.match(r'^[0-9]+\.', line) or
            re.match(r'^[A-D][\.\)]', line)):
            continue

        # 清理行內的動作描述
        clean_line = re.sub(r'（[^）]*）', '', line)
        clean_line = re.sub(r'\([^)]*\)', '', clean_line)

        match = dialogue_pattern.match(clean_line)
        if match:
            speaker = match.group(1).strip()
            content = match.group(2).strip()

            if content:
                # 記錄說話者出場順序
                if speaker not in speaker_order:
                    speaker_order.append(speaker)

                # 根據出場順序分配性別（第一個男、第二個女、交替）
                speaker_index = speaker_order.index(speaker)
                voice = 'male' if speaker_index % 2 == 0 else 'female'

                segments.append({
                    'speaker': speaker,
                    'text': content,
                    'voice': voice
                })

    return segments


def extract_dialogue_block(text: str) -> str | None:
    """從 <dialogue> 標籤中提取對話內容"""
    match = re.search(r'<dialogue>([\s\S]*?)</dialogue>', text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None


def parse_for_tts(text: str, mode: str = 'grammar') -> list[dict]:
    """
    主要解析函數：將文字轉換成 TTS segments
    """
    if not text:
        return []

    segments = []

    # 聽解模式：只解析 <dialogue> 標籤內的內容
    if mode == 'conversation':
        dialogue_block = extract_dialogue_block(text)

        if dialogue_block:
            # 只處理對話區塊（純日文）
            dialogue = parse_dialogue(dialogue_block)

            if len(dialogue) >= 1:
                # 有對話格式
                last_speaker = None

                for item in dialogue:
                    speaker = item['speaker']
                    content = item['text']
                    voice = item.get('voice', 'male')

                    # 換人說話時標記
                    speaker_changed = (speaker != last_speaker and last_speaker is not None)

                    # 按標點分割內容
                    parts = split_by_punctuation(content)

                    for i, (part_text, pause) in enumerate(parts):
                        # 清理文字
                        clean_text = clean_segment_text(part_text)
                        if not clean_text:
                            continue

                        # 對話區塊內一律用日文
                        seg = {
                            'text': clean_text,
                            'speaker': speaker,
                            'lang': 'ja',
                            'pause_after': pause,
                            'voice': voice
                        }

                        # 第一個片段且換人說話，前面加 speaker 停頓
                        if i == 0 and speaker_changed:
                            seg['pause_before'] = 'speaker'

                        segments.append(seg)

                    last_speaker = speaker

                return segments

        # 沒有 dialogue 標籤，回傳空（聽解模式不朗讀非對話內容）
        return []

    # 一般模式：清理後按標點分割
    cleaned = clean_for_tts(text)
    if not cleaned:
        return []

    parts = split_by_punctuation(cleaned)

    for part_text, pause in parts:
        # 清理文字
        clean_text = clean_segment_text(part_text)
        if not clean_text:
            continue

        # 判斷語言：有假名=日文，有中文標記=中文，其他預設日文
        if is_japanese(part_text):
            lang = 'ja'
        elif is_chinese(part_text):
            lang = 'zh'
        else:
            lang = 'ja'  # 純漢字預設日文

        segments.append({
            'text': clean_text,
            'speaker': None,
            'lang': lang,
            'pause_after': pause
        })

    return segments
