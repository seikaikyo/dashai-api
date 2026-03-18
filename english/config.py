import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    anthropic_api_key: str = os.environ.get('ANTHROPIC_API_KEY', '')
    app_passcode: str = os.environ.get('APP_PASSCODE', '')
    model: str = 'claude-sonnet-4-20250514'
    default_max_tokens: int = 300
    max_tokens_limit: int = 1200
    cors_origins: list[str] = [
        'http://localhost:5172',
        'http://127.0.0.1:5172',
        'https://ai-english-tutor.vercel.app',
        'https://english.dashai.dev',
    ]

    class Config:
        env_file = '.env'


settings = Settings()
