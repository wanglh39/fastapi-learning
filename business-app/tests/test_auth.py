"""认证端点测试：注册、登录。"""

from __future__ import annotations

import httpx
import pytest

from .conftest import register_and_login


class TestRegister:
    """POST /api/v1/auth/register"""

    async def test_register_success(self, client: httpx.AsyncClient) -> None:
        resp = await client.post(
            "/api/v1/auth/register",
            json={"email": "new@example.com", "password": "newpass123"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == "new@example.com"
        assert data["is_active"] is True
        assert data["is_superuser"] is False
        assert "id" in data
        assert "created_at" in data

    async def test_register_duplicate_email(self, client: httpx.AsyncClient) -> None:
        payload = {"email": "dup@example.com", "password": "pass12345"}
        await client.post("/api/v1/auth/register", json=payload)
        resp = await client.post("/api/v1/auth/register", json=payload)
        assert resp.status_code == 409
        assert resp.json()["code"] == "CONFLICT"

    async def test_register_short_password(self, client: httpx.AsyncClient) -> None:
        resp = await client.post(
            "/api/v1/auth/register",
            json={"email": "short@example.com", "password": "123"},
        )
        assert resp.status_code == 422

    async def test_register_invalid_email(self, client: httpx.AsyncClient) -> None:
        resp = await client.post(
            "/api/v1/auth/register",
            json={"email": "not-an-email", "password": "pass12345"},
        )
        assert resp.status_code == 422


class TestLogin:
    """POST /api/v1/auth/login"""

    async def test_login_success(self, client: httpx.AsyncClient) -> None:
        await client.post(
            "/api/v1/auth/register",
            json={"email": "login@example.com", "password": "pass12345"},
        )
        resp = await client.post(
            "/api/v1/auth/login",
            data={"username": "login@example.com", "password": "pass12345"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_wrong_password(self, client: httpx.AsyncClient) -> None:
        await client.post(
            "/api/v1/auth/register",
            json={"email": "wrong@example.com", "password": "pass12345"},
        )
        resp = await client.post(
            "/api/v1/auth/login",
            data={"username": "wrong@example.com", "password": "wrongpass"},
        )
        assert resp.status_code == 401

    async def test_login_nonexistent_user(self, client: httpx.AsyncClient) -> None:
        resp = await client.post(
            "/api/v1/auth/login",
            data={"username": "nobody@example.com", "password": "pass12345"},
        )
        assert resp.status_code == 401

    @pytest.mark.parametrize("token", ["", "invalid", "Bearer fake"])
    async def test_protected_without_valid_token(
        self, client: httpx.AsyncClient, token: str
    ) -> None:
        headers = {"Authorization": token} if token else {}
        resp = await client.get("/api/v1/users/me", headers=headers)
        assert resp.status_code == 401