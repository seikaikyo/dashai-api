"""DashAI API Gateway - 統一後端入口

三個服務掛載在路由前綴下：
  /factory/*  - Smart Factory Demo (54 CRUD + Dashboard + AI)
  /shukuyo/*  - 宿曜道占星術
  /redteam/*  - AI Red Team Toolkit
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware

from config import get_settings
from database import create_db_and_tables, load_redteam_seed, init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting DashAI API Gateway")
    create_db_and_tables()

    # Factory seed data
    from factory.router import init_factory
    init_factory()

    # Red Team seed data
    load_redteam_seed()

    # JLPT
    from jlpt.router import init_jlpt
    init_jlpt()

    # English Tutor
    from english.router import init_english
    init_english()

    yield

    # Cleanup
    from database import engine, async_engine
    engine.dispose()
    if async_engine:
        await async_engine.dispose()
    logger.info("DashAI API Gateway shut down")


app = FastAPI(
    title="DashAI API Gateway",
    description="Unified backend for Smart Factory, Shukuyo, and AI Red Team",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url=None,
    openapi_url="/openapi.json" if settings.debug else None,
)

# Rate Limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# Security Headers
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response


app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled: %s %s - %s", request.method, request.url.path, exc)
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": "Internal server error"},
    )


# Health (UptimeRobot ping target)
@app.api_route("/health", methods=["GET", "HEAD"])
def health():
    return {"status": "ok", "app": "DashAI API Gateway"}


# Root
@app.get("/")
def root():
    return {
        "app": "DashAI API Gateway",
        "version": "1.0.0",
        "services": ["/factory", "/shukuyo", "/redteam", "/jlpt", "/english"],
    }


# === Mount sub-services ===
from factory.router import router as factory_router
from shukuyo.router import router as shukuyo_router
from redteam.router import router as redteam_router

app.include_router(factory_router, prefix="/factory")
app.include_router(shukuyo_router, prefix="/shukuyo")
app.include_router(redteam_router, prefix="/redteam")

from jlpt.router import router as jlpt_router
from english.router import router as english_router

app.include_router(jlpt_router, prefix="/jlpt")
app.include_router(english_router, prefix="/english")
