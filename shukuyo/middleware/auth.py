"""Logto JWT 驗證"""
import logging
import time
from typing import Optional

import httpx
import jwt
from fastapi import Depends, HTTPException, Request
from config import get_settings

logger = logging.getLogger(__name__)

_jwks_cache: dict | None = None
_jwks_cache_time: float = 0
_JWKS_TTL = 3600  # 1 小時


async def _get_jwks(force_refresh: bool = False) -> dict:
    """取得 Logto JWKS（TTL 快取，每小時刷新）"""
    global _jwks_cache, _jwks_cache_time

    now = time.time()
    if _jwks_cache and not force_refresh and (now - _jwks_cache_time) < _JWKS_TTL:
        return _jwks_cache

    settings = get_settings()
    if not settings.logto_endpoint:
        raise HTTPException(status_code=500, detail="Logto 未設定")

    try:
        jwks_url = f"{settings.logto_endpoint}/oidc/jwks"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(jwks_url)
            resp.raise_for_status()
            _jwks_cache = resp.json()
            _jwks_cache_time = now
            return _jwks_cache
    except Exception as e:
        logger.error("JWKS 取得失敗: %s", e)
        if _jwks_cache:
            logger.warning("使用過期的 JWKS 快取")
            return _jwks_cache
        raise HTTPException(status_code=500, detail="認證服務異常")


def _extract_token(request: Request) -> Optional[str]:
    """從 Authorization header 取得 JWT"""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return None


async def get_current_user_id(request: Request) -> str:
    """驗證 JWT 並回傳 Logto user ID（受保護 API 用）"""
    token = _extract_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="未提供認證 token")

    try:
        user_id = await _verify_token(token)
        return user_id
    except jwt.InvalidTokenError:
        # 可能是 key rotation，嘗試刷新 JWKS 再驗一次
        try:
            user_id = await _verify_token(token, force_refresh=True)
            return user_id
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="token 已過期")
        except jwt.InvalidTokenError as e:
            logger.warning("JWT 驗證失敗（已刷新 JWKS）: %s", e)
            raise HTTPException(status_code=401, detail="無效的 token")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="token 已過期")


async def _verify_token(token: str, force_refresh: bool = False) -> str:
    """驗證 JWT 並回傳 user ID"""
    jwks = await _get_jwks(force_refresh=force_refresh)
    public_keys = {}
    for key_data in jwks.get("keys", []):
        kid = key_data.get("kid")
        if kid:
            public_keys[kid] = jwt.algorithms.RSAAlgorithm.from_jwk(key_data)

    unverified = jwt.get_unverified_header(token)
    kid = unverified.get("kid")
    if not kid or kid not in public_keys:
        raise jwt.InvalidTokenError("Unknown kid")

    settings = get_settings()
    payload = jwt.decode(
        token,
        key=public_keys[kid],
        algorithms=["RS256"],
        audience=settings.logto_api_resource,
        issuer=f"{settings.logto_endpoint}/oidc",
    )
    user_id = payload.get("sub")
    if not user_id:
        raise jwt.InvalidTokenError("Missing sub claim")
    return user_id


async def get_optional_user_id(request: Request) -> Optional[str]:
    """嘗試取得 user ID，未登入時回傳 None（公開 API 用）"""
    token = _extract_token(request)
    if not token:
        return None
    try:
        return await get_current_user_id(request)
    except HTTPException:
        return None
