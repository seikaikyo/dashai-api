"""JLPT Models - 使用 Gateway 共用資料庫連線"""
import logging
from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel

# 共用 engine 和 session（不再自建連線池）
from database import engine, get_session, create_db_and_tables  # noqa: F401

logger = logging.getLogger(__name__)


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
    """初始化資料庫（委託給 Gateway 共用函式）"""
    create_db_and_tables()
