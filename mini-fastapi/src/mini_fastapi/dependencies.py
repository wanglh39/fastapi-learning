"""依赖注入系统：Depends。

对应 FastAPI 源码的 `fastapi/dependencies/`。

这是 FastAPI 最精妙的设计：把"获取依赖"也变成可声明、可缓存、可测试的函数。

v0.4 实现：
- Depends 标记：声明参数由依赖函数提供
- solve_dependencies：递归解析依赖树，执行依赖函数
- 依赖缓存：同请求内同依赖函数只执行一次
- yield 依赖：用生成器实现资源初始化与清理（try/finally 语义）
- 异步依赖：支持 async def 依赖与 async yield 依赖
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Any, Callable, get_type_hints

from .exceptions import RequestValidationError
from .params import _convert, _resolve_body, is_basemodel


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


async def solve_dependencies(
    func: Any,
    path_values: dict[str, str],
    query_values: dict[str, str],
    body: bytes | None,
    cache: dict[Any, Any] | None = None,
) -> tuple[dict[str, Any], list[Callable]]:
    """递归解析并执行依赖树。

    对 func 的每个参数：
    - Depends 参数 → 递归解析子依赖，执行依赖函数，缓存结果
    - BaseModel 参数 → 请求体验证
    - 路径参数 → 类型转换
    - 查询参数 → 类型转换
    - 有默认值 → 用默认值
    - 无默认值 → 422

    Args:
        func: 端点函数或依赖函数
        path_values: 路径参数字典
        query_values: 查询参数字典
        body: 请求体字节
        cache: 依赖缓存字典（同请求内复用）

    Returns:
        (kwargs, cleaners): kwargs 是参数字典，cleaners 是 yield 依赖的清理函数列表

    Raises:
        RequestValidationError: 参数验证失败
    """
    if cache is None:
        cache = {}

    sig = inspect.signature(func)
    try:
        hints = get_type_hints(func)
    except Exception:
        hints = {}

    kwargs: dict[str, Any] = {}
    cleaners: list[Callable] = []

    for name, param in sig.parameters.items():
        annotation = hints.get(name, param.annotation)
        default = param.default

        if isinstance(default, Depends):
            kwargs[name] = await _resolve_dependency(
                default, path_values, query_values, body, cache, cleaners,
            )
        elif is_basemodel(annotation):
            kwargs[name] = _resolve_body(annotation, body, name)
        elif name in path_values:
            kwargs[name] = _convert(path_values[name], annotation, ("path", name))
        elif name in query_values:
            kwargs[name] = _convert(query_values[name], annotation, ("query", name))
        elif default is not inspect.Parameter.empty:
            kwargs[name] = default
        else:
            raise RequestValidationError(
                [{"loc": ["query", name], "msg": "field required", "type": "missing"}]
            )

    return kwargs, cleaners


async def _resolve_dependency(
    dep: Depends,
    path_values: dict[str, str],
    query_values: dict[str, str],
    body: bytes | None,
    cache: dict[Any, Any],
    cleaners: list[Callable],
) -> Any:
    """解析单个 Depends 依赖：检查缓存 → 递归解析子依赖 → 执行依赖函数。"""
    dep_func = dep.dependency
    cache_key = dep_func

    if dep.use_cache and cache_key in cache:
        return cache[cache_key]

    sub_kwargs, sub_cleaners = await solve_dependencies(
        dep_func, path_values, query_values, body, cache,
    )
    cleaners.extend(sub_cleaners)

    result, cleaner = await _call_dependency(dep_func, sub_kwargs)
    if cleaner is not None:
        cleaners.append(cleaner)

    if dep.use_cache:
        cache[cache_key] = result

    return result


async def _call_dependency(
    func: Callable[..., Any], kwargs: dict[str, Any],
) -> tuple[Any, Callable | None]:
    """调用依赖函数，处理同步/异步、yield 依赖。

    支持四种依赖函数形式：
    - 普通同步函数：直接调用
    - async def 异步函数：await 调用
    - def + yield 同步生成器：next 取值，清理时再 next
    - async def + yield 异步生成器：anext 取值，清理时再 anext

    Returns:
        (result, cleaner): result 是注入值，cleaner 是清理函数或 None
    """
    if inspect.isasyncgenfunction(func):
        gen = func(**kwargs)
        result = await gen.__anext__()

        async def cleaner() -> None:
            try:
                await gen.__anext__()
            except StopAsyncIteration:
                pass

        return result, cleaner

    if inspect.isgeneratorfunction(func):
        gen = func(**kwargs)
        result = next(gen)

        def cleaner() -> None:
            try:
                next(gen)
            except StopIteration:
                pass

        return result, cleaner

    if inspect.iscoroutinefunction(func):
        return await func(**kwargs), None

    return func(**kwargs), None
