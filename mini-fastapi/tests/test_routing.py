"""routing.py 测试：路径编译与路由匹配。

对应 src/mini_fastapi/routing.py，镜像目录结构。
"""

from __future__ import annotations

from mini_fastapi.routing import Router, compile_path


def test_compile_path_no_params() -> None:
    pattern, names = compile_path("/")
    assert names == []
    assert pattern.match("/") is not None


def test_compile_path_single_param() -> None:
    pattern, names = compile_path("/users/{user_id}")
    assert names == ["user_id"]
    matched = pattern.match("/users/42")
    assert matched is not None
    assert matched.group("user_id") == "42"


def test_compile_path_multiple_params() -> None:
    pattern, names = compile_path("/users/{user_id}/posts/{post_id}")
    assert names == ["user_id", "post_id"]
    matched = pattern.match("/users/1/posts/2")
    assert matched is not None
    assert matched.group("user_id") == "1"
    assert matched.group("post_id") == "2"


def test_compile_path_param_does_not_match_slash() -> None:
    pattern, _ = compile_path("/users/{user_id}")
    assert pattern.match("/users/1/extra") is None


def test_router_match_success() -> None:
    router = Router()

    def handler(user_id: str) -> None:
        pass

    router.add_route("/users/{user_id}", handler, methods=["GET"])
    result = router.match("GET", "/users/42")
    assert result is not None
    route, params = result
    assert params == {"user_id": "42"}
    assert route.endpoint is handler


def test_router_match_not_found() -> None:
    router = Router()

    def handler() -> None:
        pass

    router.add_route("/", handler, methods=["GET"])
    assert router.match("GET", "/missing") is None


def test_router_match_method_not_allowed() -> None:
    router = Router()

    def handler() -> None:
        pass

    router.add_route("/", handler, methods=["GET"])
    assert router.match("POST", "/") is None


def test_router_match_first_matching_route_wins() -> None:
    router = Router()

    def handler_a() -> None:
        pass

    def handler_b() -> None:
        pass

    router.add_route("/", handler_a, methods=["GET"])
    router.add_route("/", handler_b, methods=["GET"])
    result = router.match("GET", "/")
    assert result is not None
    assert result[0].endpoint is handler_a