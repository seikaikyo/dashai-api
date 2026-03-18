import os
import logging
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from .limiter import limiter
from .middleware.session import SessionMiddleware

# 載入環境變數
load_dotenv()

from .models.database import init_db
from .routers import chat, progress
from .services.api_health import api_health
from .services.question_bank_service import question_bank

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 啟動時初始化資料庫
    init_db()

    # 載入題庫
    question_bank.load()
    logger.info('題庫狀態: %s', question_bank.get_status())

    # 設定 API key 狀態
    api_health.set_has_api_key(bool(os.environ.get('ANTHROPIC_API_KEY')))

    yield


is_production = os.environ.get('ENV', 'development') == 'production'

app = FastAPI(
    title='JLPT 學習系統',
    description='AI 驅動的 JLPT N5-N1 適應性學習系統',
    version='2.0.0',
    lifespan=lifespan,
    docs_url=None if is_production else '/docs',
    redoc_url=None if is_production else '/redoc',
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS 設定（從環境變數讀取）
cors_origins_str = os.environ.get('CORS_ORIGINS', 'http://localhost:5172,http://127.0.0.1:5172')
cors_origins = [origin.strip() for origin in cors_origins_str.split(',')]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=['GET', 'POST', 'OPTIONS'],
    allow_headers=['Content-Type', 'X-Api-Key'],
)

from starlette.types import ASGIApp, Receive, Scope, Send


class SecurityHeadersMiddleware:
    """Pure ASGI 安全 headers（相容 StreamingResponse）"""
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message):
            if message['type'] == 'http.response.start':
                headers = dict(message.get('headers', []))
                extra = [
                    (b'x-content-type-options', b'nosniff'),
                    (b'x-frame-options', b'DENY'),
                    (b'referrer-policy', b'strict-origin-when-cross-origin'),
                    (b'content-security-policy', b"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com data:; connect-src 'self' https://*.onrender.com; img-src 'self' data:"),
                ]
                if is_production:
                    extra.append((b'strict-transport-security', b'max-age=31536000; includeSubDomains'))
                message['headers'] = list(message.get('headers', [])) + extra
            await send(message)

        await self.app(scope, receive, send_with_headers)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(SessionMiddleware)

# 註冊路由
app.include_router(chat.router)
app.include_router(progress.router)


@app.get('/')
async def root():
    return {
        'name': 'JLPT 學習系統',
        'version': '2.0.0',
        'endpoints': [
            '/api/chat',
            '/api/progress'
        ]
    }


@app.api_route('/health', methods=['GET', 'HEAD'])
async def health():
    return {'status': 'ok'}


@app.get('/api/status')
async def status():
    """系統狀態（API + 題庫）"""
    return {
        'api': api_health.get_status(),
        'question_bank': question_bank.get_status(),
    }
