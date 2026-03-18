import hmac
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Literal
from pydantic import BaseModel, Field
import anthropic
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from english.config import settings
from english.services.api_health import api_health
from english.services.question_bank_service import question_bank
from english.services.interview_coach import analyze_interview_answer
from english.middleware.auth import verify_passcode

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    question_bank.load()
    logger.info('題庫狀態: %s', question_bank.get_status())
    api_health.set_has_api_key(bool(settings.anthropic_api_key))
    if settings.app_passcode:
        logger.info('Passcode 已設定')
    else:
        logger.info('APP_PASSCODE 未設定，所有人可用伺服器 key')
    yield


limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title='AI English Tutor API', lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=['POST', 'GET', 'HEAD', 'OPTIONS'],
    allow_headers=['Content-Type', 'X-Api-Key', 'X-Passcode'],
)


@app.middleware('http')
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'camera=(), microphone=(self), geolocation=()'
    return response

# 預設 client（用 env key）
_default_client = None
if settings.anthropic_api_key:
    _default_client = anthropic.Anthropic(api_key=settings.anthropic_api_key, timeout=30.0)


def _get_client(request_api_key: str | None) -> anthropic.Anthropic | None:
    if request_api_key:
        return anthropic.Anthropic(api_key=request_api_key, timeout=30.0)
    return _default_client


class ChatMessage(BaseModel):
    role: Literal['user', 'assistant']
    content: str = Field(max_length=5000)


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    system_prompt: str = ''
    max_tokens: int = 0


class ChatResponse(BaseModel):
    reply: str


class InterviewFeedbackRequest(BaseModel):
    question_id: str = Field(max_length=100)
    user_answer: str = Field(max_length=10000)
    sample_answer: str = Field(max_length=5000)
    key_points: list[str]


class PasscodeRequest(BaseModel):
    passcode: str


@app.post('/api/verify-passcode')
@limiter.limit('5/minute')
def verify_passcode_endpoint(req: PasscodeRequest, request: Request):
    if not settings.app_passcode:
        return {'valid': True}
    if hmac.compare_digest(req.passcode, settings.app_passcode):
        return {'valid': True}
    raise HTTPException(status_code=401, detail='Invalid passcode')


@app.post('/api/chat', response_model=ChatResponse)
@limiter.limit('30/minute')
def chat(req: ChatRequest, request: Request):
    system_prompt = req.system_prompt or 'You are a helpful English tutor.'
    user_message = req.messages[-1].content if req.messages else ''

    # 決定用哪個 key：
    # 1. 自備 X-Api-Key → 用他的
    # 2. Passcode 正確 → 用伺服器 key
    # 3. 都沒有 → fallback 題庫
    request_api_key = request.headers.get('X-Api-Key')
    if request_api_key:
        client = _get_client(request_api_key)
    elif verify_passcode(request):
        client = _default_client
    else:
        client = None
    has_key = client is not None

    should_try = has_key and (request_api_key or api_health.should_try_api)

    if should_try:
        try:
            max_tokens = (
                min(req.max_tokens, settings.max_tokens_limit)
                if req.max_tokens > 0
                else settings.default_max_tokens
            )
            resp = client.messages.create(
                model=settings.model,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[m.model_dump() for m in req.messages],
            )
            if not request_api_key:
                api_health.mark_success()
            return ChatResponse(reply=resp.content[0].text)
        except anthropic.APIError as e:
            logger.warning('Claude API 失敗: %s', e)
            if not request_api_key:
                api_health.mark_failure()
        except Exception as e:
            logger.warning('Claude API 未預期錯誤: %s', e)
            if not request_api_key:
                api_health.mark_failure()

    reply = question_bank.get_fallback_reply(system_prompt, user_message)
    return ChatResponse(reply=reply)


@app.post('/api/interview-feedback')
@limiter.limit('20/minute')
def interview_feedback(req: InterviewFeedbackRequest, request: Request):
    request_api_key = request.headers.get('X-Api-Key')
    if request_api_key:
        client = _get_client(request_api_key)
    elif verify_passcode(request):
        client = _default_client
    else:
        client = None

    if not client:
        raise HTTPException(status_code=503, detail='API key not available')

    try:
        result = analyze_interview_answer(
            client=client,
            model=settings.model,
            question_id=req.question_id,
            user_answer=req.user_answer,
            sample_answer=req.sample_answer,
            key_points=req.key_points,
        )
        return result
    except Exception as e:
        logger.error('面試回饋分析失敗: %s', e)
        raise HTTPException(status_code=500, detail='Analysis failed')


@app.api_route('/api/health', methods=['GET', 'HEAD'])
def health():
    return {'status': 'ok'}


@app.get('/api/status')
def status(request: Request):
    if not verify_passcode(request):
        raise HTTPException(status_code=401, detail='Unauthorized')
    return {
        'api': api_health.get_status(),
        'question_bank': question_bank.get_status(),
    }
