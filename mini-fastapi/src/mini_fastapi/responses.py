"""响应对象：JSONResponse / PlainTextResponse / Response。

对应 Starlette 的 `starlette/responses.py`。

阶段 1 将实现基础 Response，通过 ASGI send 协议发送响应。
"""

from __future__ import annotations

import json
from typing import Any


class Response:
    """ASGI 响应基类。

    阶段 1 实现：通过 send 发送 http.response.start 与 http.response.body。
    """

    media_type = None

    def __init__(self, content: Any, status_code: int = 200, headers: dict[str, str] | None = None) -> None:
        self.content = content
        self.status_code = status_code
        self.headers = headers or {}

    async def __call__(self, send) -> None:
        """通过 ASGI send 协议发送响应。阶段 1 实现。"""
        raise NotImplementedError("Response 发送将在阶段 1 实现")


class JSONResponse(Response):
    """JSON 响应。"""

    media_type = "application/json"

    async def __call__(self, send) -> None:
        body = json.dumps(self.content).encode("utf-8")
        await send({
            "type": "http.response.start",
            "status": self.status_code,
            "headers": [
                (b"content-type", b"application/json; charset=utf-8"),
            ],
        })
        await send({"type": "http.response.body", "body": body})


class PlainTextResponse(Response):
    """纯文本响应。"""

    media_type = "text/plain"