"""应用核心：MiniFastAPI 类。

本模块是整个框架的入口，对应 FastAPI 源码的 `fastapi/applications.py`。

演进计划：
- v0.0: 纯 ASGI app，硬编码路由
- v0.1: 路由装饰器 + 路径参数（接入 routing.py）
- v0.2: 查询参数 + 请求体（接入 params.py + Pydantic）
- v0.3: 响应模型 + 状态码
- v0.4: 依赖注入（接入 dependencies.py）
- v0.5: OpenAPI 文档（接入 openapi.py）
- v0.6: 中间件 + 异常处理（接入 middleware.py + exceptions.py）
"""

from __future__ import annotations

import inspect
from typing import Any, Callable

from pydantic import BaseModel

from .dependencies import solve_dependencies
from .exceptions import HTTPException, RequestValidationError
from .params import parse_query_string
from .responses import JSONResponse, PlainTextResponse, Response
from .routing import Router

_BODY_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class MiniFastAPI:
    """框架应用实例。

    本身是一个合法的 ASGI 应用，可直接传给 uvicorn 运行：
        app = MiniFastAPI()
        uvicorn.run(app)
    """

    def __init__(self, *, title: str = "MiniFastAPI", version: str = "0.0.0") -> None:
        self.title = title
        self.version = version
        self.router: Router = Router()

    def get(
        self,
        path: str,
        response_model: type | None = None,
        status_code: int | None = None,
        **opts: Any,
    ) -> Callable[..., Any]:
        """注册 GET 路由。"""
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self.router.add_route(
                path, func, methods=["GET"],
                response_model=response_model, status_code=status_code, **opts,
            )
            return func
        return decorator

    def post(
        self,
        path: str,
        response_model: type | None = None,
        status_code: int | None = None,
        **opts: Any,
    ) -> Callable[..., Any]:
        """注册 POST 路由。"""
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self.router.add_route(
                path, func, methods=["POST"],
                response_model=response_model, status_code=status_code, **opts,
            )
            return func
        return decorator

    async def __call__(self, scope: dict, receive: Callable, send: Callable) -> None:
        """ASGI 协议入口，分发 lifespan 与 http 事件。"""
        if scope["type"] == "lifespan":
            await self._handle_lifespan(scope, receive, send)
            return
        if scope["type"] == "http":
            await self._handle_http(scope, receive, send)
            return

    async def _handle_lifespan(self, scope: dict, receive: Callable, send: Callable) -> None:
        """处理应用生命周期事件（启动/关闭）。"""
        while True:
            message = await receive()
            if message["type"] == "lifespan.startup":
                await send({"type": "lifespan.startup.complete"})
            elif message["type"] == "lifespan.shutdown":
                await send({"type": "lifespan.shutdown.complete"})
                break

    async def _handle_http(self, scope: dict, receive: Callable, send: Callable) -> None:
        """处理 HTTP 请求：路由匹配 → 依赖解析 → 调用端点 → 响应 → 清理。"""
        method = scope["method"]
        path = scope["path"]

        matched = self.router.match(method, path)
        if matched is None:
            await JSONResponse({"detail": "Not Found"}, status_code=404)(send)
            return

        route, path_params = matched
        query_params = parse_query_string(scope.get("query_string", b""))
        body = await self._read_body(receive) if method in _BODY_METHODS else None

        cleaners: list[Callable] = []
        try:
            try:
                kwargs, cleaners = await solve_dependencies(
                    route.endpoint, path_params, query_params, body,
                )
            except RequestValidationError as exc:
                await JSONResponse({"detail": exc.errors}, status_code=422)(send)
                return
            except HTTPException as exc:
                await JSONResponse({"detail": exc.detail}, status_code=exc.status_code)(send)
                return

            try:
                result = await self._invoke_endpoint(route.endpoint, kwargs)
            except HTTPException as exc:
                await JSONResponse({"detail": exc.detail}, status_code=exc.status_code)(send)
                return
            except Exception:
                await JSONResponse({"detail": "Internal Server Error"}, status_code=500)(send)
                return

            result = self._apply_response_model(result, route.response_model)
            response = self._coerce_result(result, route.status_code)
            await response(send)
        finally:
            await self._run_cleaners(cleaners)

    async def _run_cleaners(self, cleaners: list[Callable]) -> None:
        """按 LIFO 顺序执行 yield 依赖的清理函数。"""
        for cleaner in reversed(cleaners):
            try:
                ret = cleaner()
                if inspect.isawaitable(ret):
                    await ret
            except Exception:
                pass

    async def _read_body(self, receive: Callable) -> bytes:
        """读取完整请求体（循环直到 more_body 为假）。"""
        body = b""
        more_body = True
        while more_body:
            message = await receive()
            body += message.get("body", b"")
            more_body = message.get("more_body", False)
        return body

    async def _invoke_endpoint(self, endpoint: Callable[..., Any], kwargs: dict[str, Any]) -> Any:
        """调用端点函数，兼容同步与异步端点。"""
        if inspect.iscoroutinefunction(endpoint):
            return await endpoint(**kwargs)
        return endpoint(**kwargs)

    def _apply_response_model(self, result: Any, response_model: type | None) -> Any:
        """用 response_model 过滤输出字段。"""
        if response_model is None:
            return result
        if isinstance(result, BaseModel):
            data = result.model_dump()
        elif isinstance(result, dict):
            data = result
        else:
            data = result
        return response_model.model_validate(data).model_dump()

    def _coerce_result(self, result: Any, status_code: int | None = None) -> Response:
        """把端点返回值转为 Response 实例。"""
        code = status_code or 200
        if isinstance(result, Response):
            if status_code is not None:
                result.status_code = status_code
            return result
        if isinstance(result, (dict, list)):
            return JSONResponse(result, status_code=code)
        return PlainTextResponse(str(result), status_code=code)
