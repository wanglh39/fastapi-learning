"""中间件机制。

对应 Starlette 的 `starlette/middleware/`。

v0.6 实现：
- 纯 ASGI 中间件：__call__(scope, receive, send)
- BaseHTTPMiddleware 便捷基类
- CORS 中间件
- TimingMiddleware 请求计时
- 中间件链组装（洋葱模型）
"""

from __future__ import annotations

import time
from typing import Any, Callable


class BaseHTTPMiddleware:
    """HTTP 中间件基类。

    子类实现 async def dispatch(self, scope, receive, send, call_next)。
    call_next() 调用下一层中间件/应用。

    用法：
        class MyMiddleware(BaseHTTPMiddleware):
            async def dispatch(self, scope, receive, send, call_next):
                # 请求前逻辑
                await call_next()
                # 响应后逻辑
    """

    def __init__(self, app: Callable, **opts: Any) -> None:
        self.app = app
        for key, value in opts.items():
            setattr(self, key, value)

    async def __call__(self, scope: dict, receive: Callable, send: Callable) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def call_next() -> None:
            await self.app(scope, receive, send)

        await self.dispatch(scope, receive, send, call_next)

    async def dispatch(
        self,
        scope: dict,
        receive: Callable,
        send: Callable,
        call_next: Callable,
    ) -> None:
        raise NotImplementedError


class CORSMiddleware:
    """CORS 中间件：处理跨域请求。

    对 OPTIONS 预检请求直接返回 CORS 头；
    对普通请求在响应头中追加 CORS 头。
    """

    def __init__(
        self,
        app: Callable,
        allow_origins: list[str] | str = "*",
        allow_methods: list[str] | str = "*",
        allow_headers: list[str] | str = "*",
    ) -> None:
        self.app = app
        self.allow_origins = allow_origins
        self.allow_methods = allow_methods
        self.allow_headers = allow_headers

    async def __call__(self, scope: dict, receive: Callable, send: Callable) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        origin = self._get_origin(scope)

        if scope["method"] == "OPTIONS":
            headers = self._build_cors_headers(origin)
            await send(
                {"type": "http.response.start", "status": 200, "headers": headers}
            )
            await send({"type": "http.response.body", "body": b""})
            return

        async def send_wrapper(message: dict) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.extend(self._build_cors_headers(origin))
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_wrapper)

    def _get_origin(self, scope: dict) -> str:
        for key, value in scope.get("headers", []):
            if key == b"origin":
                return value.decode("latin-1")
        return ""

    def _build_cors_headers(self, origin: str) -> list[tuple[bytes, bytes]]:
        headers: list[tuple[bytes, bytes]] = []
        if self.allow_origins == "*":
            headers.append((b"access-control-allow-origin", b"*"))
        elif isinstance(self.allow_origins, list) and origin in self.allow_origins:
            headers.append(
                (b"access-control-allow-origin", origin.encode("latin-1"))
            )

        if self.allow_methods == "*":
            headers.append((b"access-control-allow-methods", b"*"))
        elif isinstance(self.allow_methods, list):
            methods = ", ".join(self.allow_methods).encode("latin-1")
            headers.append((b"access-control-allow-methods", methods))

        if self.allow_headers == "*":
            headers.append((b"access-control-allow-headers", b"*"))
        elif isinstance(self.allow_headers, list):
            hdrs = ", ".join(self.allow_headers).encode("latin-1")
            headers.append((b"access-control-allow-headers", hdrs))

        return headers


class TimingMiddleware:
    """请求计时中间件：在响应头中添加 X-Process-Time。"""

    def __init__(self, app: Callable) -> None:
        self.app = app

    async def __call__(self, scope: dict, receive: Callable, send: Callable) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start = time.perf_counter()

        async def send_wrapper(message: dict) -> None:
            if message["type"] == "http.response.start":
                duration = f"{time.perf_counter() - start:.6f}"
                headers = list(message.get("headers", []))
                headers.append((b"x-process-time", duration.encode("latin-1")))
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_wrapper)
