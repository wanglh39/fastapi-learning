"""inspect.signature 注解驱动验证（阶段 3 造轮子的核心技巧）。

运行：
    uv run python examples/annotation_validation.py

演示如何从端点函数的参数注解，自动区分路径参数/查询参数/请求体，
并用 Pydantic 验证。这正是 FastAPI 参数绑定的核心原理。
"""

from __future__ import annotations

import inspect
from typing import Annotated, Any, Union, get_args, get_origin, get_type_hints

from pydantic import BaseModel, Field, ValidationError


class ItemCreate(BaseModel):
    name: str
    price: float = Field(gt=0)


def list_items(
    skip: int = 0,
    limit: int = 10,
    q: str | None = None,
):
    """端点函数：skip/limit 是查询参数，q 是可选查询参数。"""
    return {"skip": skip, "limit": limit, "q": q}


def create_item(item: ItemCreate, category: str = "default"):
    """端点函数：item 是请求体（BaseModel），category 是查询参数。"""
    return {"item": item, "category": category}


def is_basemodel(annotation: Any) -> bool:
    """判断注解是否是 Pydantic BaseModel 子类。"""
    return isinstance(annotation, type) and issubclass(annotation, BaseModel)


def is_optional(annotation: Any) -> bool:
    """判断注解是否是 Optional（即 X | None）。"""
    if get_origin(annotation) is Union:
        return type(None) in get_args(annotation)
    return False


def resolve_param_kind(annotation: Any, path_param_names: set[str], param_name: str) -> str:
    """判断参数来源：path / query / body。

    Returns:
        "path" | "query" | "body"
    """
    if param_name in path_param_names:
        return "path"
    if is_basemodel(annotation):
        return "body"
    return "query"


def analyze_endpoint(func: Any, path_param_names: set[str] | None = None) -> None:
    """分析端点函数的参数注解，输出参数绑定计划。"""
    path_param_names = path_param_names or set()
    sig = inspect.signature(func)
    hints = get_type_hints(func)
    print(f"\n函数: {func.__name__}{sig}")
    print(f"{'参数':<15} {'注解':<25} {'来源':<8} {'默认':<10}")
    print("-" * 60)

    for name, param in sig.parameters.items():
        annotation = hints.get(name, param.annotation)
        kind = resolve_param_kind(annotation, path_param_names, name)
        default = "必填" if param.default is inspect.Parameter.empty else repr(param.default)
        print(f"{name:<15} {str(annotation):<25} {kind:<8} {default:<10}")


def validate_and_call(func: Any, path_params: dict, query_params: dict, body: dict | None) -> Any:
    """根据注解验证入参并调用函数（模拟 FastAPI 参数绑定）。

    Args:
        func: 端点函数
        path_params: 路径参数原始值（均为 str）
        query_params: 查询参数原始值（均为 str）
        body: 请求体原始 dict

    Returns:
        函数返回值
    """
    sig = inspect.signature(func)
    hints = get_type_hints(func)
    kwargs: dict[str, Any] = {}

    for name, param in sig.parameters.items():
        annotation = hints.get(name, param.annotation)
        has_default = param.default is not inspect.Parameter.empty

        if is_basemodel(annotation):
            if body is None:
                if has_default:
                    continue
                raise ValueError(f"缺少请求体: {name}")
            kwargs[name] = annotation.model_validate(body)
        elif name in path_params:
            kwargs[name] = _convert(path_params[name], annotation)
        elif name in query_params:
            kwargs[name] = _convert(query_params[name], annotation)
        elif has_default:
            kwargs[name] = param.default
        else:
            raise ValueError(f"缺少必填参数: {name}")

    return func(**kwargs)


def _convert(value: str, annotation: Any) -> Any:
    """把字符串值按注解类型转换。"""
    if is_optional(annotation):
        inner = [a for a in get_args(annotation) if a is not type(None)][0]
        if value is None:
            return None
        return _convert(value, inner)
    if annotation is int:
        return int(value)
    if annotation is float:
        return float(value)
    if annotation is bool:
        return value.lower() in ("true", "1", "yes")
    return value


def main() -> None:
    print("=" * 60)
    print("  注解驱动验证：从函数签名到参数绑定")
    print("=" * 60)

    analyze_endpoint(list_items)
    analyze_endpoint(create_item)
    analyze_endpoint(create_item, path_param_names={"item_id"})

    print("\n" + "=" * 60)
    print("  验证并调用")
    print("=" * 60)

    result = validate_and_call(
        list_items,
        path_params={},
        query_params={"skip": "5", "limit": "20", "q": "hello"},
        body=None,
    )
    print(f"\nlist_items(skip=5, limit=20, q=hello) → {result}")

    result = validate_and_call(
        create_item,
        path_params={},
        query_params={"category": "tools"},
        body={"name": "Widget", "price": 9.99},
    )
    print(f"create_item(body={{name:Widget, price:9.99}}, category=tools) → {result}")

    print("\n验证失败演示:")
    try:
        validate_and_call(
            create_item,
            path_params={},
            query_params={},
            body={"name": "Widget", "price": -1},
        )
    except ValidationError as exc:
        print(f"  price=-1 → ValidationError: {exc.errors()[0]['msg']}")

    print("\n完成。")


if __name__ == "__main__":
    main()