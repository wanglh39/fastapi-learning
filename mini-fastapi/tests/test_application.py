"""MiniFastAPI 应用层测试：ASGI 入口与请求分发。

对应 src/mini_fastapi/application.py，镜像目录结构。
使用 httpx ASGITransport 直接测试 ASGI app，不起真实服务器。
覆盖 v0.1（路由+路径参数）到 v0.3（response_model+status_code+HTTPException）。
"""

from __future__ import annotations

import httpx
import pytest
from pydantic import BaseModel, Field

from mini_fastapi import HTTPException, JSONResponse, MiniFastAPI


class ItemCreate(BaseModel):
    name: str = Field(min_length=1)
    price: float = Field(gt=0)


class ItemRead(BaseModel):
    name: str
    price: float


class UserRead(BaseModel):
    name: str
    age: int


def test_app_instance() -> None:
    """应用可被实例化并持有标题与版本。"""
    app = MiniFastAPI(title="Test", version="0.0.1")
    assert app.title == "Test"
    assert app.version == "0.0.1"
    assert app.router.routes == []


def _build_app() -> MiniFastAPI:
    app = MiniFastAPI(title="TestApp", version="0.3.0")

    @app.get("/")
    def root():
        return {"message": "hello"}

    @app.get("/users/{user_id}")
    def get_user(user_id: str):
        return {"user_id": user_id}

    @app.get("/users-int/{user_id}")
    def get_user_int(user_id: int):
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

    @app.get("/search")
    def search(skip: int = 0, limit: int = 10, q: str | None = None):
        return {"skip": skip, "limit": limit, "q": q}

    @app.post("/items", response_model=ItemRead, status_code=201)
    def create_item(item: ItemCreate):
        return item

    @app.post("/created", status_code=201)
    def created():
        return {"id": 1}

    @app.get("/filtered", response_model=UserRead)
    def filtered():
        return {"name": "Alice", "age": 30, "password": "secret"}

    @app.get("/teapot")
    def teapot():
        raise HTTPException(status_code=418, detail="I'm a teapot")

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


async def test_http_path_param_str() -> None:
    async with await _client() as client:
        response = await client.get("/users/42")
    assert response.status_code == 200
    assert response.json() == {"user_id": "42"}


async def test_http_path_param_int() -> None:
    async with await _client() as client:
        response = await client.get("/users-int/42")
    assert response.status_code == 200
    assert response.json() == {"user_id": 42}


async def test_http_path_param_int_invalid_422() -> None:
    async with await _client() as client:
        response = await client.get("/users-int/abc")
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert any("user_id" in err["loc"] for err in detail)


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


async def test_http_query_params_with_values() -> None:
    async with await _client() as client:
        response = await client.get("/search?skip=5&limit=20&q=hello")
    assert response.status_code == 200
    assert response.json() == {"skip": 5, "limit": 20, "q": "hello"}


async def test_http_query_params_defaults() -> None:
    async with await _client() as client:
        response = await client.get("/search")
    assert response.status_code == 200
    assert response.json() == {"skip": 0, "limit": 10, "q": None}


async def test_http_request_body_201() -> None:
    async with await _client() as client:
        response = await client.post(
            "/items", json={"name": "Widget", "price": 9.99}
        )
    assert response.status_code == 201
    assert response.json() == {"name": "Widget", "price": 9.99}


async def test_http_request_body_422() -> None:
    async with await _client() as client:
        response = await client.post(
            "/items", json={"name": "", "price": -1}
        )
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert any("body" in err["loc"] for err in detail)


async def test_http_request_body_invalid_json_422() -> None:
    async with await _client() as client:
        response = await client.post(
            "/items", content=b"not json", headers={"content-type": "application/json"}
        )
    assert response.status_code == 422


async def test_http_response_model_filter() -> None:
    async with await _client() as client:
        response = await client.get("/filtered")
    assert response.status_code == 200
    body = response.json()
    assert body == {"name": "Alice", "age": 30}
    assert "password" not in body


async def test_http_status_code() -> None:
    async with await _client() as client:
        response = await client.post("/created")
    assert response.status_code == 201
    assert response.json() == {"id": 1}


async def test_http_http_exception() -> None:
    async with await _client() as client:
        response = await client.get("/teapot")
    assert response.status_code == 418
    assert response.json() == {"detail": "I'm a teapot"}
