"""middleware.py 测试：中间件链与异常处理器。

对应 src/mini_fastapi/middleware.py，镜像目录结构。
"""

from __future__ import annotations

import httpx
import pytest

from mini_fastapi import (
    CORSMiddleware,
    HTTPException,
    JSONResponse,
    MiniFastAPI,
    TimingMiddleware,
)


# === TimingMiddleware 测试 ===


async def test_timing_middleware_adds_header() -> None:
    """TimingMiddleware 在响应头中添加 X-Process-Time。"""
    app = MiniFastAPI(title="Test", version="0.6.0")
    app.add_middleware(TimingMiddleware)

    @app.get("/")
    def root():
        return {"hello": "world"}

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")

    assert response.status_code == 200
    assert "x-process-time" in response.headers


# === CORSMiddleware 测试 ===


async def test_cors_middleware_adds_headers() -> None:
    """CORSMiddleware 在响应头中添加 CORS 头。"""
    app = MiniFastAPI(title="Test", version="0.6.0")
    app.add_middleware(CORSMiddleware, allow_origins="*")

    @app.get("/")
    def root():
        return {"hello": "world"}

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "*"


async def test_cors_middleware_options_preflight() -> None:
    """CORSMiddleware 处理 OPTIONS 预检请求。"""
    app = MiniFastAPI(title="Test", version="0.6.0")
    app.add_middleware(CORSMiddleware, allow_origins="*", allow_methods=["GET", "POST"])

    @app.get("/")
    def root():
        return {"hello": "world"}

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.options("/")

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "*"
    assert "GET" in response.headers["access-control-allow-methods"]


async def test_cors_middleware_specific_origin() -> None:
    """CORSMiddleware 只允许指定的 origin。"""
    app = MiniFastAPI(title="Test", version="0.6.0")
    app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000"])

    @app.get("/")
    def root():
        return {"hello": "world"}

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/", headers={"origin": "http://localhost:3000"})

    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


# === 中间件洋葱模型测试 ===


async def test_middleware_order_onion_model() -> None:
    """中间件按洋葱模型执行：请求从外到内，响应从内到外。"""
    log: list[str] = []

    class MiddlewareA:
        def __init__(self, app):
            self.app = app

        async def __call__(self, scope, receive, send):
            if scope["type"] != "http":
                await self.app(scope, receive, send)
                return
            log.append("A-in")

            async def send_wrapper(message):
                if message["type"] == "http.response.start":
                    log.append("A-out")
                await send(message)

            await self.app(scope, receive, send_wrapper)

    class MiddlewareB:
        def __init__(self, app):
            self.app = app

        async def __call__(self, scope, receive, send):
            if scope["type"] != "http":
                await self.app(scope, receive, send)
                return
            log.append("B-in")

            async def send_wrapper(message):
                if message["type"] == "http.response.start":
                    log.append("B-out")
                await send(message)

            await self.app(scope, receive, send_wrapper)

    app = MiniFastAPI(title="Test", version="0.6.0")
    app.add_middleware(MiddlewareA)
    app.add_middleware(MiddlewareB)

    @app.get("/")
    def root():
        log.append("endpoint")
        return {"hello": "world"}

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")

    assert response.status_code == 200
    assert log == ["A-in", "B-in", "endpoint", "B-out", "A-out"]


# === 异常处理器测试 ===


async def test_exception_handler_custom() -> None:
    """注册自定义异常处理器。"""
    class NotFoundError(Exception):
        pass

    app = MiniFastAPI(title="Test", version="0.6.0")

    @app.exception_handler(NotFoundError)
    def handle_not_found(exc: NotFoundError):
        return JSONResponse(
            {"error": "not_found", "detail": str(exc)}, status_code=404,
        )

    @app.get("/items/{item_id}")
    def get_item(item_id: int):
        if item_id == 999:
            raise NotFoundError(f"Item {item_id} not found")
        return {"item_id": item_id}

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/items/999")

    assert response.status_code == 404
    assert response.json() == {"error": "not_found", "detail": "Item 999 not found"}


async def test_exception_handler_subclass_match() -> None:
    """异常处理器支持子类匹配。"""
    class AppError(Exception):
        pass

    class DatabaseError(AppError):
        pass

    app = MiniFastAPI(title="Test", version="0.6.0")

    @app.exception_handler(AppError)
    def handle_app_error(exc: AppError):
        return JSONResponse({"error": "app_error"}, status_code=500)

    @app.get("/")
    def root():
        raise DatabaseError("connection lost")

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")

    assert response.status_code == 500
    assert response.json() == {"error": "app_error"}


async def test_exception_handler_http_exception_still_works() -> None:
    """注册自定义处理器后，未注册的 HTTPException 仍正常工作。"""
    app = MiniFastAPI(title="Test", version="0.6.0")

    @app.get("/")
    def root():
        raise HTTPException(status_code=418, detail="I'm a teapot")

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")

    assert response.status_code == 418
    assert response.json() == {"detail": "I'm a teapot"}


async def test_exception_handler_override_http_exception() -> None:
    """可以注册 HTTPException 的自定义处理器覆盖默认行为。"""
    app = MiniFastAPI(title="Test", version="0.6.0")

    @app.exception_handler(HTTPException)
    def handle_http_exc(exc: HTTPException):
        return JSONResponse(
            {"custom": True, "detail": exc.detail}, status_code=exc.status_code,
        )

    @app.get("/")
    def root():
        raise HTTPException(status_code=418, detail="teapot")

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")

    assert response.status_code == 418
    assert response.json() == {"custom": True, "detail": "teapot"}


async def test_middleware_with_normal_request() -> None:
    """中间件不影响正常的请求处理。"""
    app = MiniFastAPI(title="Test", version="0.6.0")
    app.add_middleware(TimingMiddleware)
    app.add_middleware(CORSMiddleware, allow_origins="*")

    @app.get("/users/{user_id}")
    def get_user(user_id: int):
        return {"user_id": user_id}

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/users/42")

    assert response.status_code == 200
    assert response.json() == {"user_id": 42}
    assert "x-process-time" in response.headers
    assert response.headers["access-control-allow-origin"] == "*"