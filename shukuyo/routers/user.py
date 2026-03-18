"""使用者 API - Logto 認證 + 資料同步"""
from datetime import datetime, date as date_type, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_async_session
from shukuyo.middleware.auth import get_current_user_id
from shukuyo.models.user import User, UserPartner, UserCompany, CompanyCache

router = APIRouter(prefix="/api/user", tags=["user"])


class ProfileSyncRequest(BaseModel):
    """前端 localStorage → DB 同步"""
    birth_date: str | None = None
    display_name: str | None = None
    preferences: dict | None = None


class ProfileResponse(BaseModel):
    """使用者 profile 回應"""
    id: str
    auth_id: str
    email: str | None
    display_name: str | None
    birth_date: str | None
    plan: str
    credits_remaining: int
    preferences: dict


@router.get("/profile")
async def get_profile(
    auth_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    """取得使用者 profile（自動建立）"""
    result = await session.execute(
        select(User).where(User.auth_id == auth_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        # 首次登入，建立使用者
        user = User(auth_id=auth_id)
        session.add(user)
        await session.commit()
        await session.refresh(user)

    return {
        "success": True,
        "data": ProfileResponse(
            id=user.id,
            auth_id=user.auth_id,
            email=user.email,
            display_name=user.display_name,
            birth_date=user.birth_date.isoformat() if user.birth_date else None,
            plan=user.plan,
            credits_remaining=user.credits_remaining,
            preferences=user.preferences or {},
        ).model_dump(),
    }


@router.post("/profile/sync")
async def sync_profile(
    req: ProfileSyncRequest,
    auth_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    """從 localStorage 同步 profile 到 DB"""
    result = await session.execute(
        select(User).where(User.auth_id == auth_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        user = User(auth_id=auth_id)
        session.add(user)

    if req.birth_date:
        from datetime import date
        try:
            user.birth_date = date.fromisoformat(req.birth_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="日期格式錯誤")

    if req.display_name is not None:
        user.display_name = req.display_name

    if req.preferences is not None:
        # 合併而非覆蓋，保留既有偏好
        current = user.preferences or {}
        current.update(req.preferences)
        user.preferences = current

    user.updated_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(user)

    return {
        "success": True,
        "data": ProfileResponse(
            id=user.id,
            auth_id=user.auth_id,
            email=user.email,
            display_name=user.display_name,
            birth_date=user.birth_date.isoformat() if user.birth_date else None,
            plan=user.plan,
            credits_remaining=user.credits_remaining,
            preferences=user.preferences or {},
        ).model_dump(),
    }


# ============================================================
# 完整 Profile 同步（含 partners + companies）
# ============================================================

class PartnerData(BaseModel):
    id: str
    nickname: str
    birth_date: str
    relation: str = ""

class CompanyData(BaseModel):
    id: str
    name: str
    founding_date: str = ""
    country: str = "tw"
    memo: str = ""
    job_url: str = ""

class FullSyncRequest(BaseModel):
    birth_date: str | None = None
    preferences: dict | None = None
    partners: list[PartnerData] = []
    companies: list[CompanyData] = []


@router.get("/profile/full")
async def get_full_profile(
    auth_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    """取得完整 profile（含 partners + companies）"""
    import logging
    logger = logging.getLogger(__name__)
    try:
        result = await session.execute(
            select(User).where(User.auth_id == auth_id)
        )
        user = result.scalar_one_or_none()
    except Exception as e:
        logger.error("profile/full user query failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

    if not user:
        user = User(auth_id=auth_id)
        session.add(user)
        await session.commit()
        await session.refresh(user)

    # 分開查 partners 和 companies
    try:
        partners_result = await session.execute(
            select(UserPartner).where(UserPartner.user_id == user.id)
        )
        partners = partners_result.scalars().all()
    except Exception as e:
        logger.error("profile/full partners query failed: %s", e, exc_info=True)
        partners = []

    try:
        companies_result = await session.execute(
            select(UserCompany).where(UserCompany.user_id == user.id)
        )
        companies = companies_result.scalars().all()
    except Exception as e:
        logger.error("profile/full companies query failed: %s", e, exc_info=True)
        companies = []

    return {
        "success": True,
        "data": {
            "id": user.id,
            "auth_id": user.auth_id,
            "birth_date": user.birth_date.isoformat() if user.birth_date else None,
            "plan": user.plan,
            "credits_remaining": user.credits_remaining,
            "preferences": user.preferences or {},
            "partners": [
                {
                    "id": p.id,
                    "nickname": p.nickname,
                    "birth_date": p.birth_date.isoformat(),
                    "relation": p.relation,
                }
                for p in partners
            ],
            "companies": [
                {
                    "id": c.id,
                    "name": c.name,
                    "founding_date": c.founding_date.isoformat() if c.founding_date else "",
                    "country": c.country,
                    "memo": c.memo or "",
                    "job_url": c.job_url or "",
                }
                for c in companies
            ],
        },
    }


@router.post("/profile/sync-full")
async def sync_full_profile(
    req: FullSyncRequest,
    auth_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    """同步完整 profile（含 partners + companies）到 DB"""
    result = await session.execute(
        select(User).where(User.auth_id == auth_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        user = User(auth_id=auth_id)
        session.add(user)
        await session.flush()

    # 查詢現有 partners/companies
    ep_result = await session.execute(
        select(UserPartner).where(UserPartner.user_id == user.id)
    )
    existing_partners_list = ep_result.scalars().all()

    ec_result = await session.execute(
        select(UserCompany).where(UserCompany.user_id == user.id)
    )
    existing_companies_list = ec_result.scalars().all()

    # 同步基本資料
    if req.birth_date:
        try:
            user.birth_date = date_type.fromisoformat(req.birth_date)
        except ValueError:
            pass

    if req.preferences is not None:
        current = user.preferences or {}
        current.update(req.preferences)
        user.preferences = current

    # 同步 partners（以前端為準，全量替換）
    existing_partners = {p.id: p for p in existing_partners_list}
    incoming_ids = {p.id for p in req.partners}

    # 刪除不在前端的
    for pid, partner in existing_partners.items():
        if pid not in incoming_ids:
            await session.delete(partner)

    # 新增或更新
    for p in req.partners:
        if p.id in existing_partners:
            ep = existing_partners[p.id]
            ep.nickname = p.nickname
            ep.relation = p.relation
            try:
                ep.birth_date = date_type.fromisoformat(p.birth_date)
            except ValueError:
                pass
        else:
            try:
                bd = date_type.fromisoformat(p.birth_date)
            except ValueError:
                continue
            new_partner = UserPartner(
                id=p.id,
                user_id=user.id,
                nickname=p.nickname,
                birth_date=bd,
                relation=p.relation,
            )
            session.add(new_partner)

    # 同步 companies（以前端為準，全量替換）
    existing_companies = {c.id: c for c in existing_companies_list}
    incoming_company_ids = {c.id for c in req.companies}

    for cid, company in existing_companies.items():
        if cid not in incoming_company_ids:
            await session.delete(company)

    for c in req.companies:
        fd = None
        if c.founding_date:
            try:
                fd = date_type.fromisoformat(c.founding_date)
            except ValueError:
                pass

        if c.id in existing_companies:
            ec = existing_companies[c.id]
            ec.name = c.name
            ec.country = c.country
            ec.memo = c.memo or None
            ec.job_url = c.job_url or None
            if fd:
                ec.founding_date = fd
        else:
            if not fd:
                continue  # 沒有設立日期的公司不存 DB
            new_company = UserCompany(
                id=c.id,
                user_id=user.id,
                name=c.name,
                founding_date=fd,
                country=c.country,
                memo=c.memo or None,
                job_url=c.job_url or None,
            )
            session.add(new_company)

    user.updated_at = datetime.now(timezone.utc)
    await session.commit()

    return {"success": True}


# ============================================================
# 公司資料快取（公開 API，不需登入）
# ============================================================

class CompanyCacheSaveRequest(BaseModel):
    name: str
    country: str = "tw"
    founding_date: str | None = None
    business_no: str | None = None
    source: str | None = None
    job_url_104: str | None = None


@router.get("/company-cache/{country}/{name}")
async def get_company_cache(
    country: str,
    name: str,
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    """查詢公司快取"""
    import logging
    logger = logging.getLogger(__name__)
    try:
        result = await session.execute(
            select(CompanyCache).where(
                CompanyCache.name == name,
                CompanyCache.country == country,
            )
        )
        cache = result.scalar_one_or_none()
    except Exception as e:
        logger.error("company-cache query failed: %s", e, exc_info=True)
        return {"success": False, "error": str(e)[:200]}
    if not cache:
        return {"success": True, "data": None}

    return {
        "success": True,
        "data": {
            "name": cache.name,
            "country": cache.country,
            "founding_date": cache.founding_date.isoformat() if cache.founding_date else None,
            "business_no": cache.business_no,
            "source": cache.source,
            "job_url_104": cache.job_url_104,
        },
    }


@router.post("/company-cache/batch")
async def batch_get_company_cache(
    req: dict,
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    """批次查詢公司快取（一次查多間，減少 round-trip）"""
    names: list[str] = req.get("names", [])
    country: str = req.get("country", "tw")
    if not names or len(names) > 50:
        return {"success": True, "data": {}}

    from sqlalchemy import or_
    result = await session.execute(
        select(CompanyCache).where(
            CompanyCache.country == country,
            CompanyCache.name.in_(names),
        )
    )
    caches = result.scalars().all()
    data = {}
    for cache in caches:
        if cache.founding_date:
            data[cache.name] = {
                "founding_date": cache.founding_date.isoformat(),
                "source": cache.source,
            }
    return {"success": True, "data": data}


@router.post("/company-cache")
async def save_company_cache(
    req: CompanyCacheSaveRequest,
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    """儲存公司資料到快取（公開端點，快取 GCIS 公開資料）"""
    import logging
    logger = logging.getLogger(__name__)
    try:
        result = await session.execute(
            select(CompanyCache).where(
                CompanyCache.name == req.name,
                CompanyCache.country == req.country,
            )
        )
        cache = result.scalar_one_or_none()
    except Exception as e:
        logger.error("company-cache save query failed: %s", e, exc_info=True)
        return {"success": False, "error": str(e)[:200]}

    if not cache:
        cache = CompanyCache(name=req.name, country=req.country)
        session.add(cache)

    if req.founding_date:
        from datetime import date
        try:
            cache.founding_date = date.fromisoformat(req.founding_date)
        except ValueError:
            pass

    if req.business_no:
        cache.business_no = req.business_no
    if req.source:
        cache.source = req.source
    if req.job_url_104:
        cache.job_url_104 = req.job_url_104

    cache.updated_at = datetime.utcnow()
    try:
        await session.commit()
    except Exception as e:
        logger.error("company-cache save commit failed: %s", e, exc_info=True)
        return {"success": False, "error": str(e)[:200]}

    return {"success": True}
