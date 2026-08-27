"""依赖注入系统：Depends。

对应 FastAPI 源码的 `fastapi/dependencies/`。

这是 FastAPI 最精妙的设计：把"获取依赖"也变成可声明、可缓存、可测试的函数。

演进计划（阶段 4）：
- 解析端点函数参数中的 Depends(...) 标记
- 递归构建依赖树（依赖可以依赖子依赖）
- 按拓扑顺序执行，结果注入对应参数
- 同请求内同依赖缓存（use_cache=True）
- 支持 yield 依赖：try/finally 做资源清理（如 DB 会话）
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class Depends:
    """依赖标记。

    用法：
        def get_db(): ...
        @app.get("/items")
        def list_items(db = Depends(get_db)): ...

    Attributes:
        dependency: 实际提供依赖的可调用对象
        use_cache: 是否在单次请求内缓存结果
    """

    dependency: Callable[..., Any]
    use_cache: bool = True


def solve_dependencies(func, path_params, query_params, body):
    """解析并执行依赖树，返回参数字典。

    阶段 4 实现：
    1. 用 inspect.signature 拿到 func 的参数
    2. 对每个 Depends 参数，递归 solve_dependencies
    3. 执行依赖函数，缓存结果
    4. 处理 yield 依赖的上下文管理

    Returns:
        可直接 **kwargs 传给端点函数的参数字典
    """
    raise NotImplementedError("依赖解析将在阶段 4 实现")