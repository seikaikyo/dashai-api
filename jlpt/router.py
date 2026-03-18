"""JLPT N1 Learner - 路由匯出"""
import os
import logging
from fastapi import APIRouter

from jlpt.models.database import init_db, LearningRecord, GrammarMastery, ReadingProgress  # noqa: F401
from jlpt.services.api_health import api_health
from jlpt.services.question_bank_service import question_bank
from jlpt.routers import chat, progress

logger = logging.getLogger(__name__)

router = APIRouter()
router.include_router(chat.router)
router.include_router(progress.router)


@router.get('/api/status', tags=['JLPT'])
async def jlpt_status():
    return {
        'api': api_health.get_status(),
        'question_bank': question_bank.get_status(),
    }


def init_jlpt():
    """初始化 JLPT 服務"""
    init_db()
    question_bank.load()
    logger.info('JLPT 題庫狀態: %s', question_bank.get_status())
    api_health.set_has_api_key(bool(os.environ.get('ANTHROPIC_API_KEY')))
