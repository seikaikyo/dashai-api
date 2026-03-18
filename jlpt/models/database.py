import os
import logging
from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel, create_engine, Session
from pathlib import Path

logger = logging.getLogger(__name__)

# 資料庫連線：優先使用 DATABASE_URL（PostgreSQL），fallback 到 SQLite
DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    # Neon PostgreSQL - 使用 psycopg (v3) driver
    _pg_url = DATABASE_URL.replace('postgresql://', 'postgresql+psycopg://')
    engine = create_engine(
        _pg_url,
        echo=False,
        pool_size=5,
        max_overflow=5,
        pool_timeout=10,
        pool_recycle=300,
        pool_pre_ping=True,
    )
    logger.info('使用 PostgreSQL 資料庫')
else:
    # 本地開發 SQLite fallback
    DB_PATH = Path(__file__).parent.parent.parent.parent / 'data' / 'learning.db'
    DATABASE_URL_SQLITE = f'sqlite:///{DB_PATH}'
    engine = create_engine(DATABASE_URL_SQLITE, echo=False)
    logger.info('使用 SQLite 資料庫: %s', DB_PATH)
    if os.environ.get('ENV') == 'production':
        logger.warning('生產環境未設定 DATABASE_URL，使用 SQLite（資料會在部署時遺失）')


class LearningRecord(SQLModel, table=True):
    """學習紀錄"""
    __tablename__ = 'learning_records'

    id: Optional[int] = Field(default=None, primary_key=True)
    mode: str = Field(index=True)
    level: str = Field(default='n1', index=True)
    question: str
    user_answer: str
    is_correct: bool
    grammar_point: Optional[str] = Field(default=None, index=True)
    explanation: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)


class GrammarMastery(SQLModel, table=True):
    """文法掌握度"""
    __tablename__ = 'grammar_mastery'

    id: Optional[int] = Field(default=None, primary_key=True)
    grammar_point: str = Field(index=True)
    level: str = Field(default='n1', index=True)
    correct_count: int = Field(default=0)
    total_count: int = Field(default=0)
    mastery_level: float = Field(default=0.0)
    last_practiced: datetime = Field(default_factory=datetime.now)


class ReadingProgress(SQLModel, table=True):
    """讀解進度"""
    __tablename__ = 'reading_progress'

    id: Optional[int] = Field(default=None, primary_key=True)
    total_passages: int = Field(default=0)
    correct_answers: int = Field(default=0)
    total_questions: int = Field(default=0)
    accuracy_rate: float = Field(default=0.0)
    last_practiced: datetime = Field(default_factory=datetime.now)


def init_db():
    """初始化資料庫（PostgreSQL 已透過 MCP 建好 schema，SQLite 自動建表）"""
    if not os.environ.get('DATABASE_URL'):
        # SQLite 需要自動建表
        db_path = Path(__file__).parent.parent.parent.parent / 'data' / 'learning.db'
        db_path.parent.mkdir(parents=True, exist_ok=True)
    SQLModel.metadata.create_all(engine)


def get_session():
    """取得資料庫 session"""
    with Session(engine) as session:
        yield session
