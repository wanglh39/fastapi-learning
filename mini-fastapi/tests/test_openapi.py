"""openapi.py 测试：OpenAPI 自动文档生成。

对应 src/mini_fastapi/openapi.py，镜像目录结构。
包含 get_openapi 单元测试与 ASGI 端到端测试。
"""

from __future__ import annotations

import httpx
import pytest
from pydantic import BaseModel, Field

from mini_fastapi import Depends, MiniFastAPI, get_openapi


class ItemCreate(BaseModel):
    name: str = Field(min_length=1)
    price: float = Field(gt=0)


class ItemRead(BaseModel):
    name: str
    price: float


# === get_openapi 单元测试 ===


def test_get_openapi_basic_structure() -> None:
    """OpenAPI 文档基本结构：openapi 版本、info、paths。"""
    app = MiniFastAPI(title="Test", version="1.0.0")

    @app.get("/")
    def root():
        return {"hello": "world"}

    doc = get_openapi(app.title, app.version, app.router.routes)
    assert doc["openapi"] == "3.1.0"
    assert doc["info"] == {"title": "Test", "version": "1.0.0"}
    assert "/" in doc["paths"]


def test_get_openapi_path_param() -> None:
    """路径参数生成 parameters（in: path, required: true）。"""
    app = MiniFastAPI(title="Test", version="1.0.0")

    @app.get("/users/{user_id}")
    def get_user(user_id: int):
        return {"user_id": user_id}

    doc = get_openapi(app.title, app.version, app.router.routes)
    operation = doc["paths"]["/users/{user_id}"]["get"]
    params = operation["parameters"]
    assert len(params) == 1
    assert params[0]["name"] == "user_id"
    assert params[0]["in"] == "path"
    assert params[0]["required"] is True
    assert params[0]["schema"]["type"] == "integer"


def test_get_openapi_query_param() -> None:
    """查询参数生成 parameters（in: query）。"""
    app = MiniFastAPI(title="Test", version="1.0.0")

    @app.get("/items")
    def list_items(skip: int = 0, limit: int = 10, q: str | None = None):
        return {"skip": skip}

    doc = get_openapi(app.title, app.version, app.router.routes)
    operation = doc["paths"]["/items"]["get"]
    params = {p["name"]: p for p in operation["parameters"]}
    assert params["skip"]["in"] == "query"
    assert params["skip"]["required"] is False
    assert params["skip"]["schema"]["type"] == "integer"
    assert params["limit"]["in"] == "query"
    assert params["q"]["in"] == "query"
    assert params["q"]["schema"]["type"] == "string"


def test_get_openapi_request_body() -> None:
    """BaseModel 参数生成 requestBody + components.schemas。"""
    app = MiniFastAPI(title="Test", version="1.0.0")

    @app.post("/items")
    def create_item(item: ItemCreate):
        return item

    doc = get_openapi(app.title, app.version, app.router.routes)
    operation = doc["paths"]["/items"]["post"]
    assert "requestBody" in operation
    body = operation["requestBody"]
    assert body["required"] is True
    schema = body["content"]["application/json"]["schema"]
    assert schema == {"$ref": "#/components/schemas/ItemCreate"}
    assert "ItemCreate" in doc["components"]["schemas"]


def test_get_openapi_response_model() -> None:
    """response_model 生成 responses 中的 $ref。"""
    app = MiniFastAPI(title="Test", version="1.0.0")

    @app.post("/items", response_model=ItemRead, status_code=201)
    def create_item(item: ItemCreate):
        return item

    doc = get_openapi(app.title, app.version, app.router.routes)
    operation = doc["paths"]["/items"]["post"]
    assert "201" in operation["responses"]
    resp = operation["responses"]["201"]
    schema = resp["content"]["application/json"]["schema"]
    assert schema == {"$ref": "#/components/schemas/ItemRead"}
    assert "ItemRead" in doc["components"]["schemas"]


def test_get_openapi_schema_reuse() -> None:
    """同一模型多次引用只存一份 schema。"""
    app = MiniFastAPI(title="Test", version="1.0.0")

    @app.post("/items", response_model=ItemRead)
    def create_item(item: ItemCreate):
        return item

    @app.get("/items/{item_id}", response_model=ItemRead)
    def get_item(item_id: int):
        return {"name": "x", "price": 1.0}

    doc = get_openapi(app.title, app.version, app.router.routes)
    assert "ItemRead" in doc["components"]["schemas"]
    assert "ItemCreate" in doc["components"]["schemas"]


def test_get_openapi_skips_doc_routes() -> None:
    """文档路由不出现在 OpenAPI 文档中。"""
    app = MiniFastAPI(title="Test", version="1.0.0")

    @app.get("/hello")
    def hello():
        return {"hello": "world"}

    doc = get_openapi(app.title, app.version, app.router.routes)
    assert "/openapi.json" not in doc["paths"]
    assert "/docs" not in doc["paths"]
    assert "/redoc" not in doc["paths"]
    assert "/hello" in doc["paths"]


def test_get_openapi_depends_skipped() -> None:
    """Depends 参数不出现在 operation parameters 中。"""
    app = MiniFastAPI(title="Test", version="1.0.0")

    def get_db():
        return "fake_db"

    @app.get("/items")
    def list_items(db=Depends(get_db), skip: int = 0):
        return {"skip": skip}

    doc = get_openapi(app.title, app.version, app.router.routes)
    operation = doc["paths"]["/items"]["get"]
    param_names = [p["name"] for p in operation.get("parameters", [])]
    assert "db" not in param_names
    assert "skip" in param_names


def test_get_openapi_operation_id() -> None:
    """每个 operation 有唯一 operationId。"""
    app = MiniFastAPI(title="Test", version="1.0.0")

    @app.get("/users/{user_id}")
    def get_user(user_id: int):
        return {"user_id": user_id}

    doc = get_openapi(app.title, app.version, app.router.routes)
    operation = doc["paths"]["/users/{user_id}"]["get"]
    assert "operationId" in operation
    assert "get_user" in operation["operationId"]


# === 端到端测试（ASGI transport）===


def _build_app() -> MiniFastAPI:
    app = MiniFastAPI(title="TestApp", version="0.5.0")

    @app.get("/users/{user_id}")
    def get_user(user_id: int):
        """Get User"""
        return {"user_id": user_id}

    @app.post("/items", response_model=ItemRead, status_code=201)
    def create_item(item: ItemCreate):
        """Create Item"""
        return item

    return app


async def test_http_openapi_json() -> None:
    """GET /openapi.json 返回 OpenAPI 文档。"""
    app = _build_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/openapi.json")
    assert response.status_code == 200
    doc = response.json()
    assert doc["openapi"] == "3.1.0"
    assert doc["info"]["title"] == "TestApp"
    assert "/users/{user_id}" in doc["paths"]
    assert "/items" in doc["paths"]


async def test_http_swagger_ui() -> None:
    """GET /docs 返回 Swagger UI HTML。"""
    app = _build_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/docs")
    assert response.status_code == 200
    assert "swagger-ui" in response.text.lower()
    assert "SwaggerUIBundle" in response.text


async def test_http_redoc() -> None:
    """GET /redoc 返回 ReDoc HTML。"""
    app = _build_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/redoc")
    assert response.status_code == 200
    assert "redoc" in response.text.lower()