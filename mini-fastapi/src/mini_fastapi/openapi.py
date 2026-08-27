"""OpenAPI 自动文档生成。

对应 FastAPI 源码的 `fastapi/openapi.py`。

设计哲学的集中体现：类型注解 → Pydantic schema → OpenAPI JSON → Swagger UI/ReDoc。

演进计划（阶段 5）：
- 遍历所有注册路由
- 从端点函数签名 + Pydantic 模型生成 operation 定义
- 汇总为 OpenAPI 3.1 文档
- 挂载 /openapi.json、/docs（Swagger UI）、/redoc
"""

from __future__ import annotations

from typing import Any


def get_openapi(title: str, version: str, routes: list[Any]) -> dict:
    """生成 OpenAPI 3.1 文档字典。

    阶段 5 实现：遍历 routes，为每条路由生成 paths 项与 components.schemas。

    Args:
        title: 应用标题
        version: 应用版本
        routes: 路由列表

    Returns:
        符合 OpenAPI 3.1 规范的字典
    """
    raise NotImplementedError("OpenAPI 生成将在阶段 5 实现")


def setup_docs(app) -> None:
    """为应用挂载文档路由 /openapi.json、/docs、/redoc。

    阶段 5 实现：内嵌 Swagger UI 与 ReDoc 的静态 HTML。
    """
    raise NotImplementedError("文档路由挂载将在阶段 5 实现")