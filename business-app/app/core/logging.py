"""结构化日志：structlog 配置。

阶段 8.4 实现：
- JSON 格式输出（生产）/ 彩色控制台（开发）
- 请求 trace_id 贯穿一条请求链路
- 中间件注入 trace_id 到 context
"""

from __future__ import annotations


def setup_logging(level: str = "INFO") -> None:
    """初始化 structlog 配置。阶段 8.4 实现。"""
    raise NotImplementedError