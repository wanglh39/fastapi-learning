"""应用入口：组装 FastAPI 实例。

- 加载配置
- 配置 structlog
- 注册 lifespan（数据库建表 + 连接池）
- 挂载 v1 路由
- 注册全局异常处理器
- 添加中间件（CORS、trace_id）
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .core.config import settings
from .core.exceptions import BusinessError, ConflictError, NotFoundError, PermissionDeniedError
from .core.logging import setup_logging
from .db.session import create_tables, dispose_engine
from .api.v1.router import api_router

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """应用生命周期：启动时建表，关闭时释放连接池。"""
    setup_logging(level=settings.log_level)
    logger.info("app.starting", app=settings.app_name, version=settings.app_version)
    await create_tables()
    yield
    await dispose_engine()
    logger.info("app.stopped")


class TraceIdMiddleware(BaseHTTPMiddleware):
    """为每个请求注入 trace_id 到 structlog context 和响应头。"""

    async def dispatch(self, request: Request, call_next):
        trace_id = request.headers.get("X-Trace-Id", str(uuid.uuid4()))
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(trace_id=trace_id)
        response = await call_next(request)
        response.headers["X-Trace-Id"] = trace_id
        return response


def _business_error_to_response(request: Request, exc: BusinessError) -> JSONResponse:
    """将业务异常映射为统一 JSON 响应。"""
    status_map = {
        NotFoundError: 404,
        PermissionDeniedError: 403,
        ConflictError: 409,
    }
    status_code = status_map.get(type(exc), 400)
    return JSONResponse(
        status_code=status_code,
        content={"code": exc.code, "message": exc.message},
    )


def create_app() -> FastAPI:
    """应用工厂。"""
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        openapi_url=f"{settings.api_v1_prefix}/openapi.json",
        docs_url=f"{settings.api_v1_prefix}/docs",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(TraceIdMiddleware)

    app.include_router(api_router, prefix=settings.api_v1_prefix)

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    app.add_exception_handler(NotFoundError, _business_error_to_response)
    app.add_exception_handler(PermissionDeniedError, _business_error_to_response)
    app.add_exception_handler(ConflictError, _business_error_to_response)
    app.add_exception_handler(BusinessError, _business_error_to_response)

    return app


app = create_app()
