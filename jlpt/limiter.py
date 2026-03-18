from slowapi import Limiter
from .middleware.session import get_session_key

# 使用 session ID 作為 rate limit key，比 IP 更精確
limiter = Limiter(key_func=get_session_key)
