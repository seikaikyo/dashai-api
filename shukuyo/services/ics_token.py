"""ICS 行事曆訂閱用 Token 加解密模組

使用 Fernet 對稱加密（AES-128-CBC + HMAC-SHA256）保護訂閱連結中的個人資料。
Token 有效期 400 天，過期後需重新產生。
"""

import hashlib
import logging
import os
from datetime import datetime, timedelta, timezone

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)

# Token 有效期：400 天（秒）
TOKEN_TTL_SECONDS = 400 * 24 * 60 * 60  # 34,560,000

# 初始化 Fernet 金鑰
_ics_token_secret = os.environ.get('ICS_TOKEN_SECRET')

if _ics_token_secret:
    _fernet = Fernet(_ics_token_secret.encode())
else:
    # 本機開發用：自動產生金鑰，但記錄警告
    _auto_key = Fernet.generate_key()
    _fernet = Fernet(_auto_key)
    logger.warning(
        'ICS_TOKEN_SECRET 未設定，已自動產生臨時金鑰。'
        '重啟後所有已發出的 Token 將失效。'
        '正式環境請務必設定 ICS_TOKEN_SECRET 環境變數。'
    )


def generate_token(birth_date: str, year: int) -> str:
    """加密生日與年份，產生 URL 安全的 Token 字串。

    Args:
        birth_date: 生日字串，格式 YYYY-MM-DD
        year: 年份（西元）

    Returns:
        URL 安全的加密 Token 字串
    """
    payload = f'{birth_date}|{year}'
    token = _fernet.encrypt(payload.encode())
    token_str = token.decode()

    # 稽核記錄：僅記錄 Token 雜湊，不記錄實際內容
    token_hash = hashlib.sha256(token).hexdigest()[:16]
    logger.info('ICS Token 已產生 (hash=%s)', token_hash)

    return token_str


def decrypt_token(token: str) -> tuple[str, int]:
    """解密 Token，回傳生日與年份。

    Args:
        token: 加密的 Token 字串

    Returns:
        (birth_date, year) 元組

    Raises:
        ValueError: Token 無效或已過期
    """
    try:
        payload = _fernet.decrypt(token.encode(), ttl=TOKEN_TTL_SECONDS)
    except (InvalidToken, Exception):
        # 稽核記錄：僅記錄 Token 雜湊
        token_hash = hashlib.sha256(token.encode()).hexdigest()[:16]
        logger.warning('ICS Token 解密失敗 (hash=%s)', token_hash)
        raise ValueError('Token 無效或已過期')

    decoded = payload.decode()
    parts = decoded.split('|')
    if len(parts) != 2:
        raise ValueError('Token 無效或已過期')

    birth_date = parts[0]
    try:
        year = int(parts[1])
    except ValueError:
        raise ValueError('Token 無效或已過期')

    return birth_date, year


def get_token_expiry() -> datetime:
    """取得 Token 到期時間（從現在起算 400 天）。

    Returns:
        到期日期時間（UTC）
    """
    return datetime.now(timezone.utc) + timedelta(seconds=TOKEN_TTL_SECONDS)
