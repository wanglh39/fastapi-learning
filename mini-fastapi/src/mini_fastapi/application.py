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

from typing import Any, Callable

from .routing import Route, Router


class MiniFastAPI:
    """框架应用实例。

    本身是一个合法的 ASGI 应用，可直接传给 uvicorn 运行：
        app = MiniFastAPI()
        uvicorn.run(app)

    当前实现（v0.0）：仅持有路由表，ASGI 入口待阶段 1 填充。
    """

    def __init__(self, *, title: str = "MiniFastAPI", version: str = "0.0.0") -> None:
        self.title = title
        self.version = version
        self.router: Router = Router()

    # ---- 路由装饰器（v0.1 实现真实逻辑）----
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

    # ---- ASGI 入口（阶段 1 实现）----
    async def __call__(self, scope: dict, receive: Callable, send: Callable) -> None:
        """ASGI 协议入口。

        Args:
            scope: 连接/请求元信息字典
            receive: 接收请求体的可调用对象
            send: 发送响应的可调用对象

        阶段 1 将在此实现请求分发全流程。
        """
        raise NotImplementedError("ASGI 入口将在阶段 1 实现")