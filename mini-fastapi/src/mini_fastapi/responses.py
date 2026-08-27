"""响应对象：Response / JSONResponse / PlainTextResponse。

对应 Starlette 的 `starlette/responses.py`。

通过 ASGI send 协议发送响应：先发 http.response.start（状态码与头），
再发 http.response.body（响应体）。
"""

from __future__ import annotations

import json
from typing import Any


class Response:
    """ASGI 响应基类。

    子类通过覆盖 render() 决定如何把 content 序列化为字节。
    """

    media_type: str | None = None

    def __init__(
        self,
        content: Any,
        status_code: int = 200,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.content = content
        self.status_code = status_code
        self.headers = headers or {}

    def render(self) -> bytes:
        """把 content 序列化为字节，子类覆盖。"""
        if isinstance(self.content, bytes):
            return self.content
        return str(self.content).encode("utf-8")

    async def __call__(self, send: Any) -> None:
        """通过 ASGI send 协议发送响应。"""
        body = self.render()
        header_pairs: list[tuple[bytes, bytes]] = [
            (k.lower().encode("latin-1"), v.encode("latin-1"))
            for k, v in self.headers.items()
        ]
        if self.media_type is not None:
            header_pairs.append((b"content-type", self.media_type.encode("latin-1")))
        await send(
            {
                "type": "http.response.start",
                "status": self.status_code,
                "headers": header_pairs,
            }
        )
        await send({"type": "http.response.body", "body": body})


class JSONResponse(Response):
    """JSON 响应，把 content 序列化为 JSON。"""

    media_type = "application/json; charset=utf-8"

    def render(self) -> bytes:
        return json.dumps(self.content, ensure_ascii=False).encode("utf-8")


class PlainTextResponse(Response):
    """纯文本响应。"""

    media_type = "text/plain; charset=utf-8"
