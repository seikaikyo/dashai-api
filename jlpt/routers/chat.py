from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator
from typing import Optional, Literal
from starlette.requests import Request
import json
import re
import asyncio

from ..limiter import limiter
from ..services.claude_service import (
    chat_with_claude,
    get_weak_grammar_points,
    ClaudeAPIError,
)
from ..services.learning_service import (
    get_grammar_mastery_data,
    async_get_grammar_mastery_data,
    save_learning_record,
    async_save_learning_record,
    get_weak_areas
)
from ..services.tts_service import parse_for_tts
from ..services.api_health import api_health
from ..services.question_bank_service import question_bank

import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/api/chat', tags=['chat'])


class ConversationMessage(BaseModel):
    """對話歷史訊息（驗證 role 與 content，防止 prompt injection）"""
    role: Literal['user', 'assistant']
    content: str

    @field_validator('content')
    @classmethod
    def content_length(cls, v: str) -> str:
        if len(v) > 5000:
            return v[:5000]
        return v


_API_KEY_PATTERN = re.compile(r'^sk-ant-[a-zA-Z0-9_-]{20,200}$')


def _validate_api_key(key: str | None) -> str | None:
    """驗證 API key 格式，不符合則視為無效"""
    if not key:
        return None
    if not _API_KEY_PATTERN.match(key):
        return None
    return key


class ChatRequest(BaseModel):
    mode: Literal['grammar', 'reading', 'conversation']
    level: Literal['n5', 'n4', 'n3', 'n2', 'n1'] = 'n1'
    message: str
    conversation_history: list[ConversationMessage] = []

    @field_validator('message')
    @classmethod
    def message_length(cls, v: str) -> str:
        if len(v) > 2000:
            raise ValueError('訊息長度不能超過 2000 字元')
        return v

    @field_validator('conversation_history')
    @classmethod
    def history_limit(cls, v: list) -> list:
        if len(v) > 20:
            return v[-20:]
        return v


class TTSSegmentModel(BaseModel):
    text: str
    speaker: Optional[str] = None
    lang: str = 'ja'
    pause_after: str = 'none'
    pause_before: Optional[str] = None
    voice: str = 'female'


class ChatResponse(BaseModel):
    response: str
    parsed_response: Optional[dict] = None
    mode: str
    level: str = 'n1'
    tts_segments: list[TTSSegmentModel] = []


def parse_json_response(text: str) -> Optional[dict]:
    """嘗試從回覆中解析 JSON"""
    json_match = re.search(r'```json\s*([\s\S]*?)\s*```', text)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    return None


def _is_requesting_new_question(message: str) -> bool:
    """判斷用戶是要新題還是在回答題目"""
    new_question_keywords = [
        '開始', '下一題', '繼續', '出題', '新題', '再來',
        '練習', '文法', '讀解', '聽解', '會話',
        'start', 'next', 'continue', 'new',
    ]
    msg = message.strip().lower()
    if msg in ('1', '2', '3', '4', 'a', 'b', 'c', 'd'):
        return False
    return any(kw in msg for kw in new_question_keywords) or len(msg) <= 5


def _get_fallback_response(request_mode: str, request_level: str, message: str, mastery_data: dict, weak_points: list[str]) -> str:
    """從題庫取得 fallback 回應"""
    if not question_bank.has_questions(request_mode, request_level):
        return '目前題庫尚未建立，且 AI 服務暫時無法使用。請稍後再試。'

    if _is_requesting_new_question(message):
        question = question_bank.get_question(
            mode=request_mode,
            level=request_level,
            mastery_data=mastery_data,
            weak_points=weak_points,
        )
        if question:
            return question.get('full_response', '題庫讀取錯誤')
        return '題庫已用完，請稍後再試。'
    else:
        # 嘗試對答案
        answer = question_bank.check_answer(request_mode, request_level, message)
        if answer:
            return answer
        return '請輸入 1-4 的數字回答，或輸入「下一題」繼續練習。'


@router.post('', response_model=ChatResponse)
@limiter.limit("20/minute")
async def chat(request: Request, body: ChatRequest):
    """主要對話端點（含 fallback 機制）"""
    try:
        mastery_data = await async_get_grammar_mastery_data(level=body.level)
        weak_points = get_weak_grammar_points(mastery_data, level=body.level)

        messages = [m.model_dump() for m in body.conversation_history]
        messages.append({'role': 'user', 'content': body.message})

        response_text = None

        request_api_key = _validate_api_key(request.headers.get('X-Api-Key'))
        has_key = bool(request_api_key) or api_health.should_try_api

        if has_key:
            try:
                response_text = await chat_with_claude(
                    messages=messages,
                    mode=body.mode,
                    level=body.level,
                    mastery_data=mastery_data,
                    weak_points=weak_points,
                    api_key=request_api_key,
                )
                if not request_api_key:
                    api_health.mark_success()
            except ClaudeAPIError as e:
                logger.warning('Claude API 失敗，切換到題庫模式: %s', e)
                if not request_api_key:
                    api_health.mark_failure()

        if response_text is None:
            response_text = _get_fallback_response(
                body.mode, body.level, body.message, mastery_data, weak_points
            )

        parsed = parse_json_response(response_text)
        tts_segments = parse_for_tts(response_text, body.mode)

        return ChatResponse(
            response=response_text,
            parsed_response=parsed,
            mode=body.mode,
            level=body.level,
            tts_segments=tts_segments
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error('未預期的錯誤: %s', e, exc_info=True)
        raise HTTPException(status_code=500, detail='系統暫時無法處理請求，請稍後再試')


class RecordAnswerRequest(BaseModel):
    mode: Literal['grammar', 'reading', 'conversation']
    level: Literal['n5', 'n4', 'n3', 'n2', 'n1'] = 'n1'
    question: str
    user_answer: str
    is_correct: bool
    grammar_point: Optional[str] = None
    explanation: Optional[str] = None

    @field_validator('question')
    @classmethod
    def question_length(cls, v: str) -> str:
        if len(v) > 5000:
            raise ValueError('問題長度不能超過 5000 字元')
        return v

    @field_validator('user_answer')
    @classmethod
    def answer_length(cls, v: str) -> str:
        if len(v) > 2000:
            raise ValueError('回答長度不能超過 2000 字元')
        return v


@router.post('/record')
@limiter.limit("30/minute")
async def record_answer(request: Request, body: RecordAnswerRequest):
    """記錄用戶答案"""
    try:
        record = await async_save_learning_record(
            mode=body.mode,
            level=body.level,
            question=body.question,
            user_answer=body.user_answer,
            is_correct=body.is_correct,
            grammar_point=body.grammar_point,
            explanation=body.explanation
        )
        return {
            'success': True,
            'record_id': record.id
        }
    except Exception as e:
        logger.error('記錄答案錯誤: %s', e, exc_info=True)
        raise HTTPException(status_code=500, detail='記錄答案失敗，請稍後再試')


@router.post('/stream')
@limiter.limit("20/minute")
async def chat_stream(request: Request, body: ChatRequest):
    """SSE 串流對話端點"""
    try:
        mastery_data = await async_get_grammar_mastery_data(level=body.level)
        weak_points = get_weak_grammar_points(mastery_data, level=body.level)

        messages = [m.model_dump() for m in body.conversation_history]
        messages.append({'role': 'user', 'content': body.message})

        request_api_key = _validate_api_key(request.headers.get('X-Api-Key'))
        has_key = bool(request_api_key) or api_health.should_try_api

        if not has_key:
            fallback = _get_fallback_response(
                body.mode, body.level, body.message, mastery_data, weak_points
            )

            async def fallback_gen():
                yield f"data: {json.dumps({'text': fallback}, ensure_ascii=False)}\n\n"
                parsed = parse_json_response(fallback)
                tts = parse_for_tts(fallback, body.mode)
                yield f"data: {json.dumps({'done': True, 'parsed_response': parsed, 'tts_segments': tts, 'mode': body.mode, 'level': body.level}, ensure_ascii=False)}\n\n"

            return StreamingResponse(fallback_gen(), media_type='text/event-stream')

        from ..services.claude_service import stream_with_claude

        async def event_generator():
            full_text = ''
            try:
                async for chunk in stream_with_claude(
                    messages=messages,
                    mode=body.mode,
                    level=body.level,
                    mastery_data=mastery_data,
                    weak_points=weak_points,
                    api_key=request_api_key,
                ):
                    full_text += chunk
                    yield f"data: {json.dumps({'text': chunk}, ensure_ascii=False)}\n\n"

                if not request_api_key:
                    api_health.mark_success()

            except ClaudeAPIError as e:
                logger.warning('Claude API 串流失敗: %s', e)
                if not request_api_key:
                    api_health.mark_failure()
                full_text = _get_fallback_response(
                    body.mode, body.level, body.message, mastery_data, weak_points
                )
                yield f"data: {json.dumps({'text': full_text}, ensure_ascii=False)}\n\n"

            parsed = parse_json_response(full_text)
            tts = parse_for_tts(full_text, body.mode)
            yield f"data: {json.dumps({'done': True, 'parsed_response': parsed, 'tts_segments': tts, 'mode': body.mode, 'level': body.level}, ensure_ascii=False)}\n\n"

        return StreamingResponse(event_generator(), media_type='text/event-stream')

    except HTTPException:
        raise
    except Exception as e:
        logger.error('串流錯誤: %s', e, exc_info=True)
        raise HTTPException(status_code=500, detail='系統暫時無法處理請求')
