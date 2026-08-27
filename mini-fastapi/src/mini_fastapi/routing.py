"""路由系统：Route 与 Router。

对应 FastAPI 源码的 `fastapi/routing.py` 与 Starlette 的 `starlette/routing.py`。

演进计划：
- v0.1: 路径参数提取（正则编译路径模式 /users/{id} → /users/(?P<id>[^/]+)）
- v0.2: 路由匹配后调用参数绑定
- v0.4: 路由执行前解析依赖
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class Route:
    """单条路由定义。

    Attributes:
        path: 路径模式，如 "/users/{id}"
        endpoint: 处理函数
        methods: 允许的 HTTP 方法
        pattern: 编译后的正则，用于匹配与提取路径参数
        param_names: 路径参数名列表，如 ["id"]
    """

    path: str
    endpoint: Callable[..., Any]
    methods: list[str] = field(default_factory=lambda: ["GET"])
    pattern: re.Pattern[str] = field(default_factory=lambda: re.compile("^/$"))
    param_names: list[str] = field(default_factory=list)


class Router:
    """路由表，负责注册与匹配。

    当前实现：仅存储路由，匹配逻辑在阶段 1 v0.1 填充。
    """

    def __init__(self) -> None:
        self.routes: list[Route] = []

    def add_route(self, path: str, endpoint: Callable[..., Any], methods: list[str], **opts: Any) -> None:
        """注册一条路由。

        阶段 1 将在此编译路径模式为正则，提取参数名。
        """
        route = Route(path=path, endpoint=endpoint, methods=methods)
        self.routes.append(route)

    def match(self, method: str, path: str) -> tuple[Route, dict[str, str]] | None:
        """匹配请求到路由，返回 (route, path_params) 或 None。

        阶段 1 v0.1 实现正则匹配与路径参数提取。
        """
        raise NotImplementedError("路由匹配将在阶段 1 v0.1 实现")