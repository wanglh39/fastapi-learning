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

_PARAM_RE = re.compile(r"\{(\w+)\}")


def compile_path(path: str) -> tuple[re.Pattern[str], list[str]]:
    """把路径模式编译为正则，并提取路径参数名。

    示例：
        "/users/{user_id}"           → (^/users/(?P<user_id>[^/]+)$, ["user_id"])
        "/posts/{post_id}/comments"  → (^/posts/(?P<post_id>[^/]+)/comments$, ["post_id"])

    Args:
        path: 路径模式，参数用 {name} 标记

    Returns:
        (编译后的正则, 参数名列表)
    """
    param_names = _PARAM_RE.findall(path)
    regex = _PARAM_RE.sub(r"(?P<\1>[^/]+)", path)
    pattern = re.compile(f"^{regex}$")
    return pattern, param_names


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
    """路由表，负责注册与匹配。"""

    def __init__(self) -> None:
        self.routes: list[Route] = []

    def add_route(self, path: str, endpoint: Callable[..., Any], methods: list[str], **opts: Any) -> None:
        """注册一条路由，编译路径模式为正则。"""
        pattern, param_names = compile_path(path)
        route = Route(
            path=path,
            endpoint=endpoint,
            methods=methods,
            pattern=pattern,
            param_names=param_names,
        )
        self.routes.append(route)

    def match(self, method: str, path: str) -> tuple[Route, dict[str, str]] | None:
        """匹配请求到路由，返回 (route, path_params) 或 None。

        Args:
            method: HTTP 方法，如 "GET"
            path: 请求路径，如 "/users/42"

        Returns:
            匹配成功返回 (route, 路径参数字典)，否则 None
        """
        for route in self.routes:
            if method not in route.methods:
                continue
            matched = route.pattern.match(path)
            if matched is not None:
                path_params = matched.groupdict()
                return route, path_params
        return None
