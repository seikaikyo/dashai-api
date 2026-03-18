"""AI Red Team Toolkit - 路由匯出"""
from fastapi import APIRouter

# Import models to register tables
from redteam.models import AttackTemplate  # noqa: F401

from redteam.routers import templates, tests, stats

router = APIRouter()
router.include_router(templates.router)
router.include_router(tests.router)
router.include_router(stats.router)
