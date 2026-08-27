"""dependencies.py 测试：依赖注入系统。

对应 src/mini_fastapi/dependencies.py，镜像目录结构。
包含 solve_dependencies 单元测试与 ASGI 端到端测试。
"""

from __future__ import annotations

import inspect

import httpx
import pytest

from mini_fastapi import Depends, HTTPException, MiniFastAPI
from mini_fastapi.dependencies import solve_dependencies


# === solve_dependencies 单元测试 ===


async def test_solve_no_dependencies() -> None:
    """无 Depends 参数时，行为与 resolve_params 一致。"""
    def handler(skip: int = 0, limit: int = 10) -> None:
        pass

    kwargs, cleaners = await solve_dependencies(handler, {}, {"skip": "5", "limit": "20"}, None)
    assert kwargs == {"skip": 5, "limit": 20}
    assert cleaners == []


async def test_solve_basic_depends() -> None:
    """基本 Depends 注入：依赖函数返回值直接作为参数值。"""
    def get_db():
        return "fake_db"

    def handler(db=Depends(get_db)) -> None:
        pass

    kwargs, cleaners = await solve_dependencies(handler, {}, {}, None)
    assert kwargs == {"db": "fake_db"}
    assert cleaners == []


async def test_solve_nested_depends() -> None:
    """嵌套依赖：handler → get_current_user → get_token。"""
    def get_token():
        return "abc123"

    def get_current_user(token=Depends(get_token)):
        return {"username": "alice", "token": token}

    def handler(user=Depends(get_current_user)) -> None:
        pass

    kwargs, cleaners = await solve_dependencies(handler, {}, {}, None)
    assert kwargs["user"] == {"username": "alice", "token": "abc123"}


async def test_solve_depends_with_query_params() -> None:
    """依赖函数本身可以接收查询参数。"""
    def get_pagination(skip: int = 0, limit: int = 10):
        return {"skip": skip, "limit": limit}

    def handler(pagination=Depends(get_pagination)) -> None:
        pass

    kwargs, cleaners = await solve_dependencies(handler, {}, {"skip": "5", "limit": "20"}, None)
    assert kwargs["pagination"] == {"skip": 5, "limit": 20}


async def test_solve_depends_cache() -> None:
    """同请求内同依赖函数只执行一次，结果缓存复用。"""
    call_count = 0

    def get_counter():
        nonlocal call_count
        call_count += 1
        return call_count

    def handler(a=Depends(get_counter), b=Depends(get_counter)) -> None:
        pass

    kwargs, cleaners = await solve_dependencies(handler, {}, {}, None)
    assert call_count == 1
    assert kwargs["a"] == kwargs["b"] == 1


async def test_solve_depends_no_cache() -> None:
    """use_cache=False 时每次都重新执行。"""
    call_count = 0

    def get_counter():
        nonlocal call_count
        call_count += 1
        return call_count

    def handler(
        a=Depends(get_counter, use_cache=False),
        b=Depends(get_counter, use_cache=False),
    ) -> None:
        pass

    kwargs, cleaners = await solve_dependencies(handler, {}, {}, None)
    assert call_count == 2
    assert kwargs["a"] == 1
    assert kwargs["b"] == 2


async def test_solve_yield_dependency() -> None:
    """yield 依赖：yield 前执行，yield 值注入，清理函数待调用。"""
    cleanup_log: list[str] = []

    def get_session():
        cleanup_log.append("open")
        yield {"active": True}
        cleanup_log.append("close")

    def handler(session=Depends(get_session)) -> None:
        pass

    kwargs, cleaners = await solve_dependencies(handler, {}, {}, None)
    assert kwargs["session"] == {"active": True}
    assert cleanup_log == ["open"]
    assert len(cleaners) == 1
    cleaners[0]()
    assert cleanup_log == ["open", "close"]


async def test_solve_async_dependency() -> None:
    """async def 依赖函数。"""
    async def get_async_value():
        return 42

    def handler(val=Depends(get_async_value)) -> None:
        pass

    kwargs, cleaners = await solve_dependencies(handler, {}, {}, None)
    assert kwargs["val"] == 42


async def test_solve_async_yield_dependency() -> None:
    """async def + yield 依赖。"""
    cleanup_log: list[str] = []

    async def get_async_session():
        cleanup_log.append("open")
        yield {"active": True}
        cleanup_log.append("close")

    def handler(session=Depends(get_async_session)) -> None:
        pass

    kwargs, cleaners = await solve_dependencies(handler, {}, {}, None)
    assert kwargs["session"] == {"active": True}
    assert cleanup_log == ["open"]
    assert len(cleaners) == 1
    ret = cleaners[0]()
    if inspect.isawaitable(ret):
        await ret
    assert cleanup_log == ["open", "close"]


async def test_solve_depends_with_path_params() -> None:
    """Depends 与路径参数混合。"""
    def get_item(item_id: int):
        return {"id": item_id, "name": "Widget"}

    def handler(item_id: int, item=Depends(get_item)) -> None:
        pass

    kwargs, cleaners = await solve_dependencies(handler, {"item_id": "42"}, {}, None)
    assert kwargs["item_id"] == 42
    assert kwargs["item"] == {"id": 42, "name": "Widget"}


# === 端到端测试（ASGI transport）===


def _build_app() -> MiniFastAPI:
    app = MiniFastAPI(title="DepApp", version="0.4.0")

    _store = [
        {"id": 1, "name": "Widget"},
        {"id": 2, "name": "Gadget"},
        {"id": 3, "name": "Doohickey"},
    ]

    def get_store():
        return _store

    def get_pagination(skip: int = 0, limit: int = 10):
        return {"skip": skip, "limit": limit}

    def get_token(q: str | None = None):
        return q

    def get_current_user(token: str = Depends(get_token)):
        if token == "secret":
            return {"username": "alice", "role": "admin"}
        raise HTTPException(status_code=401, detail="Unauthorized")

    session_log: list[str] = []

    def get_session():
        session_log.append("open")
        yield {"active": True}
        session_log.append("close")

    @app.get("/dep-items")
    def dep_items(store=Depends(get_store), pagination=Depends(get_pagination)):
        s = pagination["skip"]
        return store[s : s + pagination["limit"]]

    @app.get("/me")
    def me(user=Depends(get_current_user)):
        return user

    @app.get("/session")
    def use_session(session=Depends(get_session)):
        return {"active": session["active"]}

    @app.get("/session-log")
    def session_log_endpoint():
        return {"log": list(session_log)}

    return app


async def test_http_depends_injection() -> None:
    """端到端：Depends 注入存储与分页。"""
    app = _build_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/dep-items?skip=1&limit=10")
    assert response.status_code == 200
    assert response.json() == [{"id": 2, "name": "Gadget"}, {"id": 3, "name": "Doohickey"}]


async def test_http_nested_depends_auth_success() -> None:
    """端到端：嵌套 Depends 认证成功。"""
    app = _build_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/me?q=secret")
    assert response.status_code == 200
    assert response.json() == {"username": "alice", "role": "admin"}


async def test_http_nested_depends_auth_failure() -> None:
    """端到端：嵌套 Depends 认证失败 → 401。"""
    app = _build_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/me?q=wrong")
    assert response.status_code == 401
    assert response.json() == {"detail": "Unauthorized"}


async def test_http_yield_dependency_cleanup() -> None:
    """端到端：yield 依赖在请求结束后执行清理。"""
    app = _build_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/session")
        assert response.status_code == 200
        assert response.json() == {"active": True}

        log_response = await client.get("/session-log")
        assert "open" in log_response.json()["log"]
        assert "close" in log_response.json()["log"]