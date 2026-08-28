"""测试夹具：内存 SQLite 数据库 + AsyncClient + 认证辅助。"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator

import httpx
import pytest
import pytest_asyncio
from httpx import ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_session
from app.main import app
from app.models import Article, Tag, User  # noqa: F401  确保模型注册

TEST_DATABASE_URL = "sqlite+aiosqlite://"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    poolclass=StaticPool,
    connect_args={"check_same_thread": False},
)
test_session_factory = async_sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)


@pytest.fixture(scope="session")
def event_loop():
    """全局事件循环。"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(autouse=True)
async def setup_database() -> AsyncGenerator[None, None]:
    """每个测试前建表，测试后清表。"""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def session() -> AsyncGenerator[AsyncSession, None]:
    """提供测试数据库会话。"""
    async with test_session_factory() as s:
        yield s


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """提供 HTTP 测试客户端，注入测试数据库会话。"""
    async def override_get_session() -> AsyncGenerator[AsyncSession, None]:
        async with test_session_factory() as s:
            yield s

    app.dependency_overrides[get_session] = override_get_session
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


async def register_and_login(
    client: httpx.AsyncClient,
    email: str = "test@example.com",
    password: str = "testpass123",
) -> str:
    """注册并登录，返回 access_token。"""
    await client.post("/api/v1/auth/register", json={"email": email, "password": password})
    resp = await client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    return resp.json()["access_token"]


@pytest_asyncio.fixture
async def auth_token(client: httpx.AsyncClient) -> str:
    """提供已登录用户的 access_token。"""
    return await register_and_login(client)


@pytest_asyncio.fixture
async def auth_headers(auth_token: str) -> dict:
    """提供认证请求头。"""
    return {"Authorization": f"Bearer {auth_token}"}