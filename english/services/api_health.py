"""API 可用性偵測服務

lazy check + 60 秒冷卻機制。
不做啟動時 health check（省 token）。
"""

import time


class APIHealthChecker:
    """追蹤 Claude API 可用性狀態"""

    def __init__(self, cooldown_seconds: int = 60):
        self._cooldown = cooldown_seconds
        self._last_failure_time: float = 0
        self._is_available: bool = True
        self._has_api_key: bool = False

    def set_has_api_key(self, has_key: bool):
        """設定是否有 API key"""
        self._has_api_key = has_key

    @property
    def should_try_api(self) -> bool:
        """判斷是否該嘗試呼叫 API"""
        if not self._has_api_key:
            return False
        if self._is_available:
            return True
        return (time.time() - self._last_failure_time) >= self._cooldown

    @property
    def is_available(self) -> bool:
        return self._is_available and self._has_api_key

    def mark_success(self):
        """API 呼叫成功"""
        self._is_available = True
        self._last_failure_time = 0

    def mark_failure(self):
        """API 呼叫失敗"""
        self._is_available = False
        self._last_failure_time = time.time()

    def get_status(self) -> dict:
        """回傳目前狀態"""
        cooldown_remaining = 0
        if not self._is_available and self._last_failure_time > 0:
            elapsed = time.time() - self._last_failure_time
            cooldown_remaining = max(0, self._cooldown - elapsed)

        return {
            'api_available': self._is_available,
            'cooldown_remaining_seconds': round(cooldown_remaining),
        }


# 全域單例
api_health = APIHealthChecker()
