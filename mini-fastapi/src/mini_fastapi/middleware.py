"""中间件机制。

对应 Starlette 的 `starlette/middleware/`。

演进计划（阶段 6）：
- 实现中间件洋葱模型：请求从外到内，响应从内到外
- 提供 BaseHTTPMiddleware 便捷基类
- 内置 CORS、计时日志示例中间件
- 中间件链与路由分发的组装顺序
"""

from __future__ import annotations

from typing import Any, Callable


class BaseHTTPMiddleware:
    """HTTP 中间件基类。

    子类实现 async def dispatch(self, request, call_next)。
    阶段 6 实现。
    """

    async def dispatch(self, request: Any, call_next: Callable) -> Any:
        raise NotImplementedError


def add_middleware(app, middleware_cls, **opts: Any) -> None:
    """向应用添加中间件。阶段 6 实现。"""
    raise NotImplementedError