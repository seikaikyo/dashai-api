"""Shukuyo (宿曜道) - 路由匯出"""
from fastapi import APIRouter

# Import models to register tables
from shukuyo.models.stats import UsageStats  # noqa: F401
from shukuyo.models.user import User, UserPartner, UserCompany, CompanyCache  # noqa: F401

from shukuyo.routers import sukuyodo
from shukuyo.routers import user

router = APIRouter()
router.include_router(sukuyodo.router, prefix="/api/sukuyodo", tags=["Shukuyo"])
router.include_router(user.router, tags=["Shukuyo - User"])
