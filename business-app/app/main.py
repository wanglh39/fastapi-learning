"""应用入口：组装 FastAPI 实例。

阶段 8 逐步填充：配置加载、路由挂载、中间件、异常处理器、日志、 lifespan 数据库连接池。
"""

from __future__ import annotations

from fastapi import FastAPI

from .core.config import settings


def create_app() -> FastAPI:
    """应用工厂。

    阶段 8 实现：
    - 加载配置
    - 配置 structlog
    - 注册 lifespan（数据库连接池）
    - 挂载 v1 路由
    - 注册全局异常处理器
    - 添加中间件（CORS、trace_id）
    """
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        openapi_url=f"{settings.api_v1_prefix}/openapi.json",
        docs_url=f"{settings.api_v1_prefix}/docs",
    )

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    return app


app = create_app()