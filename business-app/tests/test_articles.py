"""文章端点测试：CRUD、分页、权限。"""

from __future__ import annotations

import httpx

from .conftest import register_and_login


class TestCreateArticle:
    """POST /api/v1/articles/"""

    async def test_create_success(self, client: httpx.AsyncClient, auth_headers: dict) -> None:
        resp = await client.post(
            "/api/v1/articles/",
            json={"title": "Hello", "content": "World", "tag_ids": []},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Hello"
        assert data["content"] == "World"
        assert "id" in data
        assert "author_id" in data
        assert data["tags"] == []

    async def test_create_without_token(self, client: httpx.AsyncClient) -> None:
        resp = await client.post(
            "/api/v1/articles/",
            json={"title": "No Auth", "content": "Body"},
        )
        assert resp.status_code == 401

    async def test_create_validation_error(self, client: httpx.AsyncClient, auth_headers: dict) -> None:
        resp = await client.post(
            "/api/v1/articles/",
            json={"title": "", "content": "Body"},
            headers=auth_headers,
        )
        assert resp.status_code == 422


class TestReadArticle:
    """GET /api/v1/articles/{id}"""

    async def test_read_success(self, client: httpx.AsyncClient, auth_headers: dict) -> None:
        create = await client.post(
            "/api/v1/articles/",
            json={"title": "Read Me", "content": "Content"},
            headers=auth_headers,
        )
        article_id = create.json()["id"]
        resp = await client.get(f"/api/v1/articles/{article_id}")
        assert resp.status_code == 200
        assert resp.json()["title"] == "Read Me"

    async def test_read_not_found(self, client: httpx.AsyncClient) -> None:
        resp = await client.get("/api/v1/articles/99999")
        assert resp.status_code == 404


class TestListArticles:
    """GET /api/v1/articles/"""

    async def test_list_empty(self, client: httpx.AsyncClient) -> None:
        resp = await client.get("/api/v1/articles/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_list_with_data(self, client: httpx.AsyncClient, auth_headers: dict) -> None:
        for i in range(3):
            await client.post(
                "/api/v1/articles/",
                json={"title": f"Article {i}", "content": "Body"},
                headers=auth_headers,
            )
        resp = await client.get("/api/v1/articles/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3
        assert data["page"] == 1
        assert data["size"] == 20

    async def test_list_pagination(self, client: httpx.AsyncClient, auth_headers: dict) -> None:
        for i in range(5):
            await client.post(
                "/api/v1/articles/",
                json={"title": f"Page {i}", "content": "Body"},
                headers=auth_headers,
            )
        resp = await client.get("/api/v1/articles/?page=1&size=2")
        data = resp.json()
        assert len(data["items"]) == 2
        assert data["total"] == 5
        assert data["pages"] == 3


class TestUpdateArticle:
    """PUT /api/v1/articles/{id}"""

    async def test_update_success(self, client: httpx.AsyncClient, auth_headers: dict) -> None:
        create = await client.post(
            "/api/v1/articles/",
            json={"title": "Original", "content": "Old"},
            headers=auth_headers,
        )
        article_id = create.json()["id"]
        resp = await client.put(
            f"/api/v1/articles/{article_id}",
            json={"title": "Updated", "content": "New"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated"
        assert resp.json()["content"] == "New"

    async def test_update_partial(self, client: httpx.AsyncClient, auth_headers: dict) -> None:
        create = await client.post(
            "/api/v1/articles/",
            json={"title": "Keep", "content": "Keep"},
            headers=auth_headers,
        )
        article_id = create.json()["id"]
        resp = await client.put(
            f"/api/v1/articles/{article_id}",
            json={"title": "Changed"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "Changed"
        assert resp.json()["content"] == "Keep"

    async def test_update_by_non_author(self, client: httpx.AsyncClient, auth_headers: dict) -> None:
        create = await client.post(
            "/api/v1/articles/",
            json={"title": "Owner", "content": "Body"},
            headers=auth_headers,
        )
        article_id = create.json()["id"]
        token2 = await register_and_login(client, "other@example.com", "otherpass123")
        resp = await client.put(
            f"/api/v1/articles/{article_id}",
            json={"title": "Hacked"},
            headers={"Authorization": f"Bearer {token2}"},
        )
        assert resp.status_code == 403
        assert resp.json()["code"] == "PERMISSION_DENIED"

    async def test_update_not_found(self, client: httpx.AsyncClient, auth_headers: dict) -> None:
        resp = await client.put(
            "/api/v1/articles/99999",
            json={"title": "Nope"},
            headers=auth_headers,
        )
        assert resp.status_code == 404


class TestDeleteArticle:
    """DELETE /api/v1/articles/{id}"""

    async def test_delete_success(self, client: httpx.AsyncClient, auth_headers: dict) -> None:
        create = await client.post(
            "/api/v1/articles/",
            json={"title": "Delete Me", "content": "Body"},
            headers=auth_headers,
        )
        article_id = create.json()["id"]
        resp = await client.delete(f"/api/v1/articles/{article_id}", headers=auth_headers)
        assert resp.status_code == 204
        verify = await client.get(f"/api/v1/articles/{article_id}")
        assert verify.status_code == 404

    async def test_delete_by_non_author(self, client: httpx.AsyncClient, auth_headers: dict) -> None:
        create = await client.post(
            "/api/v1/articles/",
            json={"title": "Protected", "content": "Body"},
            headers=auth_headers,
        )
        article_id = create.json()["id"]
        token2 = await register_and_login(client, "other@example.com", "otherpass123")
        resp = await client.delete(
            f"/api/v1/articles/{article_id}",
            headers={"Authorization": f"Bearer {token2}"},
        )
        assert resp.status_code == 403

    async def test_delete_not_found(self, client: httpx.AsyncClient, auth_headers: dict) -> None:
        resp = await client.delete("/api/v1/articles/99999", headers=auth_headers)
        assert resp.status_code == 404


class TestHealthEndpoint:
    """GET /health"""

    async def test_health(self, client: httpx.AsyncClient) -> None:
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}