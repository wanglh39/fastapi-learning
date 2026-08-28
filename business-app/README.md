# business-app

FastAPI 博客 API 业务实践项目，演示规范化工程化开发。

## 技术栈

- FastAPI + Uvicorn
- SQLAlchemy 2.0 async + aiosqlite / asyncpg + Alembic
- Pydantic v2 + pydantic-settings
- JWT（python-jose）+ bcrypt 密码哈希
- structlog 结构化日志 + trace_id
- pytest + httpx（30 测试）

## 分层架构

```
api (路由/契约) → service (业务逻辑) → repository (数据访问) → model (ORM)
```

## 运行

```bash
cp .env.example .env
uv sync
uv run uvicorn app.main:app --reload
```

文档：http://127.0.0.1:8000/api/v1/docs

## 测试

```bash
uv sync --extra test
uv run pytest
```

## Docker

```bash
docker compose up --build
```

app 服务在 `localhost:8000`，PostgreSQL 在 `localhost:5432`。

## API 端点

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | /api/v1/auth/register | 注册 |
| POST | /api/v1/auth/login | 登录 |
| GET | /api/v1/users/me | 当前用户 |
| GET | /api/v1/users/{id} | 查询用户 |
| GET | /api/v1/articles/ | 文章列表 |
| POST | /api/v1/articles/ | 创建文章 |
| GET | /api/v1/articles/{id} | 文章详情 |
| PUT | /api/v1/articles/{id} | 更新（仅作者） |
| DELETE | /api/v1/articles/{id} | 删除（仅作者） |
