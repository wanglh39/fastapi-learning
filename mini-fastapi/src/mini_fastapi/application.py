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

from .responses import JSONResponse, PlainTextResponse, Response
from .routing import Router


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

    def get(self, path: str, **opts: Any) -> Callable[..., Any]:
        """注册 GET 路由。"""
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self.router.add_route(path, func, methods=["GET"], **opts)
            return func
        return decorator

    def post(self, path: str, **opts: Any) -> Callable[..., Any]:
        """注册 POST 路由。"""
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self.router.add_route(path, func, methods=["POST"], **opts)
            return func
        return decorator

    async def __call__(self, scope: dict, receive: Callable, send: Callable) -> None:
        """ASGI 协议入口，分发 lifespan 与 http 事件。

        Args:
            scope: 连接/请求元信息字典
            receive: 接收事件的异步可调用
            send: 发送事件的异步可调用
        """
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
        """处理 HTTP 请求：路由匹配 → 调用端点 → 发送响应。"""
        method = scope["method"]
        path = scope["path"]

        matched = self.router.match(method, path)
        if matched is None:
            await JSONResponse({"detail": "Not Found"}, status_code=404)(send)
            return

        route, path_params = matched
        try:
            result = await self._invoke_endpoint(route.endpoint, path_params)
        except Exception:
            await JSONResponse({"detail": "Internal Server Error"}, status_code=500)(send)
            return

        response = self._coerce_result(result)
        await response(send)

    async def _invoke_endpoint(self, endpoint: Callable[..., Any], path_params: dict[str, str]) -> Any:
        """调用端点函数，兼容同步与异步端点。"""
        if inspect.iscoroutinefunction(endpoint):
            return await endpoint(**path_params)
        return endpoint(**path_params)

    def _coerce_result(self, result: Any) -> Response:
        """把端点返回值转为 Response 实例。"""
        if isinstance(result, Response):
            return result
        if isinstance(result, (dict, list)):
            return JSONResponse(result)
        return PlainTextResponse(str(result))
