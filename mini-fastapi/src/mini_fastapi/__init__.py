"""mini-fastapi: 从零实现的类 FastAPI 轻量级框架。

通过亲手实现 FastAPI 的核心能力来理解其内部机制：
- ASGI 应用与路由
- 基于类型注解的参数绑定（Pydantic）
- 依赖注入系统（Depends）
- OpenAPI 自动文档生成
- 中间件与异常处理

版本里程碑见仓库根 README。
"""

from .application import MiniFastAPI

__all__ = ["MiniFastAPI"]
__version__ = "0.0.0"