from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """應用程式設定"""

    # 應用資訊
    app_name: str = "Sukuyodo API"
    app_version: str = "1.0.0"
    debug: bool = False

    # 資料庫
    database_url: str = ""

    # Clerk 認證
    clerk_secret_key: str = ""

    # CORS
    cors_origins: list[str] = [
        "http://localhost:5171",  # sukuyodo 固定 port
        "http://localhost:5176",  # shukuyo v2 固定 port
        "http://localhost:3000",
        "https://sukuyodo.vercel.app",
        "https://sukuyodo.dashai.dev",
        "https://shukuyo.vercel.app",
        "https://shukuyo.dashai.dev",
    ]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
