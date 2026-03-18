"""DashAI API Gateway - 統一設定"""
import os
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # Gateway
    debug: bool = False

    # 資料庫 (共用 Neon PostgreSQL)
    database_url: str = ""

    # === Factory 相關 ===
    # (factory 不需額外 key，公開 API)

    # === Shukuyo 相關 ===
    clerk_secret_key: str = ""

    # === Red Team 相關 ===
    app_api_key: str = ""

    # === English Tutor 相關 ===
    app_passcode: str = ""
    english_model: str = "claude-sonnet-4-20250514"
    english_default_max_tokens: int = 300
    english_max_tokens_limit: int = 1200

    # === LLM API Keys (共用) ===
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    custom_llm_base_url: str = "http://localhost:11434/v1"
    custom_llm_api_key: str = ""

    # Rate Limiting
    rate_limit: str = "30/minute"
    rate_limit_test: str = "10/minute"
    ai_rate_limit: int = 3
    ai_daily_limit: int = 50

    # CORS (合併所有前端 origins)
    cors_origins: list[str] = [
        # factory
        "http://localhost:5173",
        "http://localhost:5174",
        "https://factory.dashai.dev",
        "https://smart-factory-demo.vercel.app",
        "https://smart-factory-demo-git-main-seikaikyos-projects.vercel.app",
        "https://smart-factory-demo-seikaikyos-projects.vercel.app",
        # shukuyo
        "http://localhost:5171",
        "http://localhost:5176",
        "https://sukuyodo.vercel.app",
        "https://sukuyodo.dashai.dev",
        "https://shukuyo.vercel.app",
        "https://shukuyo.dashai.dev",
        # ai-red-team
        "http://localhost:5175",
        "https://ai-red-team.dashai.dev",
        "https://ai-red-team.vercel.app",
        # ai-english-tutor
        "https://english.dashai.dev",
        "https://ai-english-tutor.vercel.app",
        # jlpt
        "http://localhost:5172",
        "https://jlpt.dashai.dev",
        "https://jlpt-n1-learner.vercel.app",
    ]

    # Shukuyo app 相關
    app_name: str = "DashAI API Gateway"
    app_version: str = "1.0.0"


@lru_cache
def get_settings() -> Settings:
    return Settings()


# === Factory 相容性 (factory/config.py 的舊 API) ===
_settings = get_settings()
DATABASE_URL = _settings.database_url
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
CORS_ORIGINS = _settings.cors_origins
