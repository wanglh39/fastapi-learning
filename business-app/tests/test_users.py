"""用户端点测试：me、get by id。"""

from __future__ import annotations

import httpx


class TestCurrentUser:
    """GET /api/v1/users/me"""

    async def test_get_me(self, client: httpx.AsyncClient, auth_headers: dict) -> None:
        resp = await client.get("/api/v1/users/me", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "test@example.com"
        assert data["is_active"] is True

    async def test_get_me_without_token(self, client: httpx.AsyncClient) -> None:
        resp = await client.get("/api/v1/users/me")
        assert resp.status_code == 401


class TestGetUser:
    """GET /api/v1/users/{user_id}"""

    async def test_get_user_by_id(self, client: httpx.AsyncClient, auth_headers: dict) -> None:
        me = await client.get("/api/v1/users/me", headers=auth_headers)
        user_id = me.json()["id"]
        resp = await client.get(f"/api/v1/users/{user_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["email"] == "test@example.com"

    async def test_get_user_not_found(self, client: httpx.AsyncClient, auth_headers: dict) -> None:
        resp = await client.get("/api/v1/users/99999", headers=auth_headers)
        assert resp.status_code == 404
        assert resp.json()["code"] == "NOT_FOUND"