"""业务异常定义。

自定义异常类携带业务语义，由全局异常处理器映射为 HTTP 响应。
"""

from __future__ import annotations


class BusinessError(Exception):
    """业务异常基类。"""

    def __init__(self, message: str, code: str = "BUSINESS_ERROR") -> None:
        self.message = message
        self.code = code
        super().__init__(message)


class NotFoundError(BusinessError):
    """资源不存在。"""

    def __init__(self, resource: str, resource_id: int | str) -> None:
        super().__init__(f"{resource} {resource_id} 不存在", code="NOT_FOUND")


class PermissionDeniedError(BusinessError):
    """权限不足。"""

    def __init__(self, message: str = "权限不足") -> None:
        super().__init__(message, code="PERMISSION_DENIED")


class ConflictError(BusinessError):
    """资源冲突（如邮箱已注册）。"""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="CONFLICT")