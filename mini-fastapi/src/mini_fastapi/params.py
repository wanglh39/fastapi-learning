"""参数绑定：Path / Query / Body 等参数标记。

对应 FastAPI 源码的 `fastapi/params.py`。

演进计划：
- v0.2: 根据 inspect.signature 解析端点函数参数注解，
        将基本类型(int/str/float/bool)视为查询参数，
        将 Pydantic BaseModel 子类视为请求体，
        支持 Annotated[int, Path(...)] / Query(...) / Body(...) 显式标记。
- v0.2: 参数验证失败时返回 422 错误响应（结构对齐 FastAPI）。
"""

from __future__ import annotations

from dataclasses import dataclass


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


def resolve_params(func):
    """解析端点函数的参数注解，生成参数绑定计划。

    阶段 2 v0.2 实现：用 inspect.signature 拿到每个参数的 annotation，
    按类型分类为 path / query / body，并记录是否必填、默认值等。

    Args:
        func: 端点处理函数

    Returns:
        参数绑定计划（待定义的数据结构）
    """
    raise NotImplementedError("参数绑定将在阶段 3 v0.2 实现")