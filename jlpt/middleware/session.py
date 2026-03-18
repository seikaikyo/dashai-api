"""匿名 Session 中介層 (Pure ASGI)

每位訪客自動分配 session token，儲存在 httpOnly cookie。
不需要使用者帳號，但提供：
- 更精確的 rate limiting（per session 取代 per IP）
- CSRF 防護（SameSite=Strict）
- 不可被 JS 讀取（httpOnly）
"""

import os
import uuid
from http.cookies import SimpleCookie
from starlette.requests import Request
from starlette.types import ASGIApp, Receive, Scope, Send


SESSION_COOKIE_NAME = 'jlpt_session'
is_production = os.environ.get('ENV', 'development') == 'production'


class SessionMiddleware:
    """Pure ASGI session middleware（相容 StreamingResponse）"""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return

        # 從 cookie 取得 session ID
        headers = dict(scope.get('headers', []))
        cookie_header = headers.get(b'cookie', b'').decode()
        session_id = None

        if cookie_header:
            cookie = SimpleCookie()
            cookie.load(cookie_header)
            if SESSION_COOKIE_NAME in cookie:
                session_id = cookie[SESSION_COOKIE_NAME].value

        is_new = False
        if not session_id:
            session_id = str(uuid.uuid4())
            is_new = True

        # 存到 scope.state 供 request.state 使用
        if 'state' not in scope:
            scope['state'] = {}
        scope['state']['session_id'] = session_id

        async def send_with_cookie(message):
            if message['type'] == 'http.response.start' and is_new:
                # 只在新 session 時設定 cookie
                secure = '; Secure' if is_production else ''
                cookie_value = (
                    f'{SESSION_COOKIE_NAME}={session_id}; '
                    f'HttpOnly; SameSite=Strict; Max-Age=2592000; Path=/{secure}'
                )
                headers_list = list(message.get('headers', []))
                headers_list.append((b'set-cookie', cookie_value.encode()))
                message['headers'] = headers_list
            await send(message)

        await self.app(scope, receive, send_with_cookie)


def get_session_key(request: Request) -> str:
    """Rate limit key: session + IP 組合（防止清 cookie 繞過）"""
    session_id = getattr(request.state, 'session_id', '')
    client_ip = request.client.host if request.client else '0.0.0.0'
    if session_id:
        return f'{session_id}:{client_ip}'
    return client_ip
