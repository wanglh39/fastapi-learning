"""纯 ASGI 示例：不依赖任何框架，直接实现 ASGI 协议。

运行：
    uv run uvicorn examples.asgi_raw:app --reload

    GET /            → {"message": "hello, raw ASGI"}
    GET /echo?msg=hi → {"msg": "hi"}
    其他             → 404

本示例用于理解 ASGI 协议三要素：scope / receive / send。
"""

from urllib.parse import parse_qs


async def app(scope, receive, send):
    assert scope["type"] == "http"

    path = scope["path"]
    method = scope["method"]

    if path == "/" and method == "GET":
        await _send_json(send, 200, {"message": "hello, raw ASGI"})
        return

    if path == "/echo" and method == "GET":
        query_string = scope.get("query_string", b"")
        params = parse_qs(query_string.decode("utf-8"))
        msg = params.get("msg", [""])[0]
        await _send_json(send, 200, {"msg": msg})
        return

    await _send_json(send, 404, {"detail": "Not Found"})


async def _send_json(send, status, payload):
    import json

    body = json.dumps(payload).encode("utf-8")
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [(b"content-type", b"application/json; charset=utf-8")],
        }
    )
    await send({"type": "http.response.body", "body": body})