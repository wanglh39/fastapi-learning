"""参数绑定：Path / Query / Body 标记与参数解析。

对应 FastAPI 源码的 `fastapi/params.py` 与 `fastapi/dependencies/utils.py`。

v0.2 实现：
- 根据 inspect.signature + get_type_hints 解析端点函数参数注解
- BaseModel 子类 → 请求体（Pydantic 验证，失败转 422）
- 基本类型(int/str/float/bool) → 路径或查询参数（类型转换）
> - 参数验证失败时抛 RequestValidationError, 由 application 转为 422 响应
"""

from __future__ import annotations

import inspect
import json
from dataclasses import dataclass
from typing import Any, Union, get_args, get_origin, get_type_hints
from urllib.parse import parse_qs

from pydantic import BaseModel, ValidationError

from .exceptions import RequestValidationError


@dataclass
class Param:
    """参数元信息基类。"""

    default: object | None = None


@dataclass
class Path(Param):
    """路径参数标记。"""


@dataclass
class Query(Param):
    """查询参数标记。"""


@dataclass
class Body(Param):
    """请求体标记。"""


def is_basemodel(annotation: Any) -> bool:
    """判断注解是否是 Pydantic BaseModel 子类。"""
    return isinstance(annotation, type) and issubclass(annotation, BaseModel)


def is_optional(annotation: Any) -> bool:
    """判断注解是否是 Optional（即 X | None）。"""
    if get_origin(annotation) is Union:
        return type(None) in get_args(annotation)
    return False


def unpack_optional(annotation: Any) -> Any:
    """从 Optional[X] 中取出 X。"""
    args = get_args(annotation)
    return next(a for a in args if a is not type(None))


def parse_query_string(query_string: bytes) -> dict[str, str]:
    """解析 ASGI query_string（字节）为单值字典。"""
    parsed = parse_qs(query_string.decode("utf-8"))
    return {key: values[0] for key, values in parsed.items()}


def _convert(value: str, annotation: Any, loc: tuple[str, ...]) -> Any:
    """把字符串值按注解类型转换，失败抛 RequestValidationError。"""
    if is_optional(annotation):
        if value is None:
            return None
        annotation = unpack_optional(annotation)
    try:
        if annotation is int:
            return int(value)
        if annotation is float:
            return float(value)
        if annotation is bool:
            return value.lower() in ("true", "1", "yes")
        return value
    except (ValueError, TypeError):
        raise RequestValidationError(
            [
                {
                    "loc": list(loc),
                    "msg": f"value is not a valid {annotation}",
                    "type": "type_error",
                }
            ]
        )


def _resolve_body(model: type[BaseModel], body: bytes | None, name: str) -> BaseModel:
    """解析请求体并用 Pydantic 验证，失败抛 RequestValidationError。"""
    if not body:
        raise RequestValidationError(
            [{"loc": ["body", name], "msg": "field required", "type": "missing"}]
        )
    try:
        data = json.loads(body)
    except (json.JSONDecodeError, ValueError):
        raise RequestValidationError(
            [{"loc": ["body"], "msg": "Expecting value", "type": "value_error.jsondecode"}]
        )
    try:
        return model.model_validate(data)
    except ValidationError as exc:
        errors = []
        for err in exc.errors():
            err = dict(err)
            err["loc"] = ["body"] + list(err["loc"])
            errors.append(err)
        raise RequestValidationError(errors)


def resolve_params(
    func: Any,
    path_param_names: list[str],
    path_values: dict[str, str],
    query_values: dict[str, str],
    body: bytes | None,
) -> dict[str, Any]:
    """解析端点函数参数，返回可直接 **kwargs 传入的参数字典。

    Args:
        func: 端点处理函数
        path_param_names: 路径模式中的参数名列表
        path_values: 从 URL 提取的路径参数值（均为 str）
        query_values: 从查询串解析的参数值（均为 str）
        body: 原始请求体字节（可能为 None）

    Returns:
        参数字典

    Raises:
        RequestValidationError: 参数验证失败（转为 422）
    """
    sig = inspect.signature(func)
    try:
        hints = get_type_hints(func)
    except Exception:
        hints = {}

    kwargs: dict[str, Any] = {}

    for name, param in sig.parameters.items():
        annotation = hints.get(name, param.annotation)
        has_default = param.default is not inspect.Parameter.empty

        if is_basemodel(annotation):
            kwargs[name] = _resolve_body(annotation, body, name)
        elif name in path_values:
            kwargs[name] = _convert(path_values[name], annotation, ("path", name))
        elif name in query_values:
            kwargs[name] = _convert(query_values[name], annotation, ("query", name))
        elif has_default:
            kwargs[name] = param.default
        else:
            raise RequestValidationError(
                [{"loc": ["query", name], "msg": "field required", "type": "missing"}]
            )

    return kwargs
