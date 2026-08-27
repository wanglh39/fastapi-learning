"""MiniFastAPI 应用层测试：ASGI 入口与请求分发。

对应 src/mini_fastapi/application.py，镜像目录结构。
使用 httpx ASGITransport 直接测试 ASGI app，不起真实服务器。
"""

from __future__ import annotations

import httpx
import pytest

from mini_fastapi import JSONResponse, MiniFastAPI


def test_app_instance() -> None:
    """应用可被实例化并持有标题与版本。"""
    app = MiniFastAPI(title="Test", version="0.0.1")
    assert app.title == "Test"
    assert app.version == "0.0.1"
    assert app.router.routes == []


def _build_app() -> MiniFastAPI:
    app = MiniFastAPI(title="TestApp", version="0.1.0")

    @app.get("/")
    def root():
        return {"message": "hello"}

    @app.get("/users/{user_id}")
    def get_user(user_id: str):
        return {"user_id": user_id}

    @app.get("/users/{user_id}/posts/{post_id}")
    def get_post(user_id: str, post_id: str):
        return {"user_id": user_id, "post_id": post_id}

    @app.post("/echo")
    def echo():
        return {"echo": True}

    @app.get("/async")
    async def async_endpoint():
        return {"async": True}

    @app.get("/custom-response")
    def custom_response():
        return JSONResponse({"custom": True}, status_code=201)

    @app.get("/error")
    def error_endpoint():
        raise RuntimeError("boom")

    return app


async def _client() -> httpx.AsyncClient:
    app = _build_app()
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://test")


async def test_http_get_root() -> None:
    async with await _client() as client:
        response = await client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "hello"}


async def test_http_path_param() -> None:
    async with await _client() as client:
        response = await client.get("/users/42")
    assert response.status_code == 200
    assert response.json() == {"user_id": "42"}


async def test_http_nested_path_params() -> None:
    async with await _client() as client:
        response = await client.get("/users/1/posts/2")
    assert response.status_code == 200
    assert response.json() == {"user_id": "1", "post_id": "2"}


async def test_http_404_not_found() -> None:
    async with await _client() as client:
        response = await client.get("/missing")
    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}


async def test_http_post() -> None:
    async with await _client() as client:
        response = await client.post("/echo")
    assert response.status_code == 200
    assert response.json() == {"echo": True}


async def test_http_async_endpoint() -> None:
    async with await _client() as client:
        response = await client.get("/async")
    assert response.status_code == 200
    assert response.json() == {"async": True}


async def test_http_custom_response() -> None:
    async with await _client() as client:
        response = await client.get("/custom-response")
    assert response.status_code == 201
    assert response.json() == {"custom": True}


async def test_http_endpoint_exception_returns_500() -> None:
    async with await _client() as client:
        response = await client.get("/error")
    assert response.status_code == 500
    assert response.json() == {"detail": "Internal Server Error"}
