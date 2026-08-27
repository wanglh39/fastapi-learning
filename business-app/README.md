# business-app

FastAPI 博客 API 业务实践项目，演示规范化工程化开发。

## 技术栈

- FastAPI + Uvicorn
- SQLAlchemy 2.0 async + asyncpg + Alembic
- Pydantic v2 + pydantic-settings
- JWT（python-jose）+ passlib bcrypt
- structlog 结构化日志
- pytest + httpx + testcontainers

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

## 阶段对应

本项目在阶段 8 逐步实现，各模块顶部 docstring 标注了实现计划。