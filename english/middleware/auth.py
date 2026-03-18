import hmac
import logging

from fastapi import Request

from english.config import settings

logger = logging.getLogger(__name__)


def verify_passcode(request: Request) -> bool:
    """驗證 passcode。沒設 APP_PASSCODE 就放行所有人。"""
    if not settings.app_passcode:
        return True

    passcode = request.headers.get('X-Passcode') or ''
    return hmac.compare_digest(passcode, settings.app_passcode)
