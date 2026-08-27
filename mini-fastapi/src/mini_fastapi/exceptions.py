"""异常处理。

对应 FastAPI 源码的 `fastapi/exceptions.py` 与 Starlette 的异常处理。

演进计划（阶段 6）：
- HTTPException：携带 status_code 与 detail
- 异常处理器注册：@app.exception_handler(SomeException)
- 全局兜底：未捕获异常 → 500
- 请求验证异常 → 422（结构对齐 FastAPI）
"""

from __future__ import annotations

from typing import Any


class HTTPException(Exception):
    """HTTP 异常，可由端点直接抛出以中断并返回指定状态码。

    Attributes:
        status_code: HTTP 状态码
        detail: 错误详情
    """

    def __init__(self, status_code: int, detail: Any = None) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


class RequestValidationError(Exception):
    """请求参数验证失败。阶段 3 v0.2 引入，映射为 422。"""

    def __init__(self, errors: list[dict]) -> None:
        self.errors = errors
        super().__init__(errors)