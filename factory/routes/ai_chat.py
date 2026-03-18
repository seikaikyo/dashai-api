"""AI Chat endpoint with function calling."""

import os
import json
import logging
import time
from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlmodel import Session
from database import get_session
from factory.services.ai_tools import TOOLS, execute_tool, _factory_briefing
from factory.services.ai_provider import chat_completion, format_tool_result, AI_PROVIDER

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/ai', tags=['AI Assistant'])

MAX_TOOL_ROUNDS = 5

# -- Rate limiting --
RATE_LIMIT_WINDOW = 3600  # 1 hour
RATE_LIMIT_MAX = int(os.getenv('AI_RATE_LIMIT', '3'))  # per IP per hour
DAILY_LIMIT_MAX = int(os.getenv('AI_DAILY_LIMIT', '50'))  # global daily cap
_rate_store: dict[str, list[float]] = defaultdict(list)
_daily_count = 0
_daily_reset_ts = time.time()


def _check_rate_limit(request: Request) -> None:
    global _daily_count, _daily_reset_ts
    now = time.time()

    # Reset daily counter every 24h
    if now - _daily_reset_ts > 86400:
        _daily_count = 0
        _daily_reset_ts = now

    # Global daily cap
    if _daily_count >= DAILY_LIMIT_MAX:
        raise HTTPException(
            status_code=429,
            detail=f'Daily limit reached ({DAILY_LIMIT_MAX} requests). Resets in {int(86400 - (now - _daily_reset_ts)) // 3600}h.',
        )

    # Per-IP per-minute
    ip = request.client.host if request.client else 'unknown'
    window_start = now - RATE_LIMIT_WINDOW
    _rate_store[ip] = [t for t in _rate_store[ip] if t > window_start]

    if len(_rate_store[ip]) >= RATE_LIMIT_MAX:
        raise HTTPException(
            status_code=429,
            detail=f'Too many requests. Max {RATE_LIMIT_MAX} per hour.',
        )

    _rate_store[ip].append(now)
    _daily_count += 1


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]


class ToolCallInfo(BaseModel):
    name: str
    arguments: dict
    result: dict


class ChatResponse(BaseModel):
    success: bool
    reply: str
    tool_calls: list[ToolCallInfo] = []
    error: str | None = None


def _check_api_key() -> None:
    """Check that the required API key is set."""
    provider = AI_PROVIDER
    if provider == 'claude':
        if not os.getenv('ANTHROPIC_API_KEY'):
            raise HTTPException(status_code=503, detail='ANTHROPIC_API_KEY not configured')
    else:
        if not os.getenv('OPENAI_API_KEY'):
            raise HTTPException(status_code=503, detail='OPENAI_API_KEY not configured')


@router.post('/chat', response_model=ChatResponse)
def chat(req: ChatRequest, request: Request, session: Session = Depends(get_session)):
    # BYOK: user provides own API key via headers
    user_api_key = request.headers.get('x-ai-key', '')
    user_provider = request.headers.get('x-ai-provider', '')
    is_byok = bool(user_api_key)

    if not is_byok:
        # Server key mode: rate limit applies
        _check_rate_limit(request)
        _check_api_key()

    messages = [{'role': m.role, 'content': m.content} for m in req.messages]
    all_tool_calls: list[ToolCallInfo] = []

    try:
        for _round in range(MAX_TOOL_ROUNDS):
            resp = chat_completion(
                messages, TOOLS,
                user_api_key=user_api_key,
                user_provider=user_provider,
            )

            if not resp['tool_calls']:
                return ChatResponse(
                    success=True,
                    reply=resp['content'] or '',
                    tool_calls=all_tool_calls,
                )

            results = []
            for tc in resp['tool_calls']:
                result = execute_tool(tc['name'], tc['arguments'], session)
                results.append(result)
                all_tool_calls.append(ToolCallInfo(
                    name=tc['name'],
                    arguments=tc['arguments'],
                    result=result,
                ))
                logger.info('Tool call: %s(%s) -> %d items',
                            tc['name'],
                            json.dumps(tc['arguments'], ensure_ascii=False),
                            result.get('count', 0))

            messages = format_tool_result(
                messages, resp['tool_calls'], results,
                user_provider=user_provider,
            )

        resp = chat_completion(
            messages, [],
            user_api_key=user_api_key,
            user_provider=user_provider,
        )
        return ChatResponse(
            success=True,
            reply=resp['content'] or '',
            tool_calls=all_tool_calls,
        )

    except Exception as e:
        logger.exception('AI chat error')
        return ChatResponse(
            success=False,
            reply='',
            error=str(e),
        )


@router.get('/briefing')
def briefing(lang: str = 'zh-TW', session: Session = Depends(get_session)):
    """Quick factory briefing without LLM - pure data query."""
    return {
        'success': True,
        'data': _factory_briefing(session, lang=lang),
    }


@router.get('/status')
def ai_status():
    """Check AI provider status and configuration."""
    provider = AI_PROVIDER
    has_key = bool(
        os.getenv('ANTHROPIC_API_KEY') if provider == 'claude'
        else os.getenv('OPENAI_API_KEY')
    )
    return {
        'success': True,
        'data': {
            'provider': provider,
            'model': (
                os.getenv('ANTHROPIC_MODEL', 'claude-sonnet-4-20250514')
                if provider == 'claude'
                else os.getenv('OPENAI_MODEL', 'gpt-4o')
            ),
            'configured': has_key,
            'tools': [t['function']['name'] for t in TOOLS],
            'daily_used': _daily_count,
            'daily_limit': DAILY_LIMIT_MAX,
            'daily_remaining': max(DAILY_LIMIT_MAX - _daily_count, 0),
        },
    }
