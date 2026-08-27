"""responses.py 测试：ASGI 响应发送。

对应 src/mini_fastapi/responses.py，镜像目录结构。
"""

from __future__ import annotations

import json
from typing import Any

from mini_fastapi.responses import JSONResponse, PlainTextResponse, Response


async def _collect(response: Response) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []

    async def send(msg: dict[str, Any]) -> None:
        messages.append(msg)

    await response(send)
    return messages


async def test_json_response_basic() -> None:
    response = JSONResponse({"msg": "hello"})
    messages = await _collect(response)
    assert messages[0]["type"] == "http.response.start"
    assert messages[0]["status"] == 200
    assert messages[1]["type"] == "http.response.body"
    assert json.loads(messages[1]["body"]) == {"msg": "hello"}


async def test_json_response_status_code() -> None:
    response = JSONResponse({"detail": "Not Found"}, status_code=404)
    messages = await _collect(response)
    assert messages[0]["status"] == 404


async def test_json_response_chinese_not_escaped() -> None:
    response = JSONResponse({"msg": "你好"})
    messages = await _collect(response)
    assert messages[1]["body"] == b'{"msg": "\xe4\xbd\xa0\xe5\xa5\xbd"}'


async def test_plain_text_response() -> None:
    response = PlainTextResponse("hello")
    messages = await _collect(response)
    assert messages[1]["body"] == b"hello"
    headers = dict(messages[0]["headers"])
    assert headers[b"content-type"] == b"text/plain; charset=utf-8"


async def test_response_custom_headers() -> None:
    response = PlainTextResponse("hi", headers={"x-custom": "value"})
    messages = await _collect(response)
    headers = dict(messages[0]["headers"])
    assert headers[b"x-custom"] == b"value"


async def test_response_bytes_content() -> None:
    response = Response(b"raw bytes")
    messages = await _collect(response)
    assert messages[1]["body"] == b"raw bytes"