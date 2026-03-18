"""DashAI API Gateway - 統一資料庫連線"""
import json
import logging
from pathlib import Path

from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _is_sqlite(url: str) -> bool:
    return not url or url.startswith("sqlite")


def _build_sync_url(url: str) -> str:
    if _is_sqlite(url):
        return url or "sqlite:///./dashai.db"
    return url.replace("postgresql://", "postgresql+psycopg://")


def _build_async_url(url: str) -> str:
    if _is_sqlite(url):
        return (url or "sqlite:///./dashai.db").replace("sqlite:///", "sqlite+aiosqlite:///")
    import re
    async_url = url.replace("postgresql://", "postgresql+asyncpg://")
    # asyncpg 不支援 sslmode / channel_binding query params，需移除
    for param in ["sslmode", "channel_binding"]:
        async_url = re.sub(rf'[?&]{param}=[^&]*', '', async_url)
    async_url = async_url.replace('?&', '?').rstrip('?').rstrip('&')
    return async_url


# 同步引擎
_url = settings.database_url
if _is_sqlite(_url):
    engine = create_engine(
        _build_sync_url(_url),
        connect_args={"check_same_thread": False},
    )
else:
    engine = create_engine(
        _build_sync_url(_url),
        pool_size=5,
        max_overflow=5,
        pool_timeout=10,
        pool_recycle=300,
        pool_pre_ping=True,
    )

# 非同步引擎 (shukuyo 用)
if not _is_sqlite(_url):
    import ssl as ssl_module
    _ssl_ctx = ssl_module.create_default_context()
    async_engine = create_async_engine(
        _build_async_url(_url),
        connect_args={"ssl": _ssl_ctx},
        pool_size=3,
        max_overflow=2,
        pool_recycle=300,
        pool_pre_ping=True,
    )
    AsyncSessionLocal = sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )
else:
    async_engine = None
    AsyncSessionLocal = None


def get_session():
    with Session(engine) as session:
        yield session


async def get_async_session():
    if AsyncSessionLocal is None:
        raise RuntimeError("Async DB not available (SQLite mode)")
    async with AsyncSessionLocal() as session:
        yield session


def create_db_and_tables():
    """建立所有資料表"""
    SQLModel.metadata.create_all(engine)


def init_db():
    """create_db_and_tables 的別名 (shukuyo/redteam 相容)"""
    create_db_and_tables()


def load_redteam_seed():
    """載入 Red Team seed data"""
    from redteam.models import AttackTemplate

    with Session(engine) as session:
        count = session.query(AttackTemplate).count()
        if count > 0:
            return
        seed_path = Path(__file__).parent / "redteam" / "seed" / "templates.json"
        if not seed_path.exists():
            return
        templates = json.loads(seed_path.read_text(encoding="utf-8"))
        for t in templates:
            session.add(AttackTemplate(**t))
        session.commit()
        logger.info("Seed: loaded %d attack templates", len(templates))
