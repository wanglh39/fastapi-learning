"""params.py 测试：参数解析与绑定。

对应 src/mini_fastapi/params.py，镜像目录结构。
"""

from __future__ import annotations

import json

import pytest
from pydantic import BaseModel, Field

from mini_fastapi.exceptions import RequestValidationError
from mini_fastapi.params import parse_query_string, resolve_params


class ItemCreate(BaseModel):
    name: str = Field(min_length=1)
    price: float = Field(gt=0)


def test_parse_query_string_basic() -> None:
    result = parse_query_string(b"skip=5&limit=20")
    assert result == {"skip": "5", "limit": "20"}


def test_parse_query_string_empty() -> None:
    assert parse_query_string(b"") == {}


def test_resolve_path_int_conversion() -> None:
    def handler(user_id: int) -> None:
        pass

    kwargs = resolve_params(handler, ["user_id"], {"user_id": "42"}, {}, None)
    assert kwargs == {"user_id": 42}
    assert isinstance(kwargs["user_id"], int)


def test_resolve_path_float_conversion() -> None:
    def handler(rate: float) -> None:
        pass

    kwargs = resolve_params(handler, ["rate"], {"rate": "3.14"}, {}, None)
    assert kwargs == {"rate": 3.14}


def test_resolve_query_params_with_defaults() -> None:
    def handler(skip: int = 0, limit: int = 10) -> None:
        pass

    kwargs = resolve_params(handler, [], {}, {"skip": "5", "limit": "20"}, None)
    assert kwargs == {"skip": 5, "limit": 20}


def test_resolve_query_params_uses_default_when_missing() -> None:
    def handler(skip: int = 0, limit: int = 10) -> None:
        pass

    kwargs = resolve_params(handler, [], {}, {}, None)
    assert kwargs == {"skip": 0, "limit": 10}


def test_resolve_optional_query_none() -> None:
    def handler(q: str | None = None) -> None:
        pass

    kwargs = resolve_params(handler, [], {}, {}, None)
    assert kwargs == {"q": None}


def test_resolve_optional_query_with_value() -> None:
    def handler(q: str | None = None) -> None:
        pass

    kwargs = resolve_params(handler, [], {}, {"q": "hello"}, None)
    assert kwargs == {"q": "hello"}


def test_resolve_body_basemodel() -> None:
    def handler(item: ItemCreate) -> None:
        pass

    body = json.dumps({"name": "Widget", "price": 9.99}).encode()
    kwargs = resolve_params(handler, [], {}, {}, body)
    assert kwargs["item"].name == "Widget"
    assert kwargs["item"].price == 9.99


def test_resolve_body_validation_error_422() -> None:
    def handler(item: ItemCreate) -> None:
        pass

    body = json.dumps({"name": "", "price": -1}).encode()
    with pytest.raises(RequestValidationError) as exc_info:
        resolve_params(handler, [], {}, {}, body)
    errors = exc_info.value.errors
    assert any("body" in err["loc"] for err in errors)


def test_resolve_invalid_int_conversion_422() -> None:
    def handler(user_id: int) -> None:
        pass

    with pytest.raises(RequestValidationError):
        resolve_params(handler, ["user_id"], {"user_id": "abc"}, {}, None)


def test_resolve_missing_required_body_422() -> None:
    def handler(item: ItemCreate) -> None:
        pass

    with pytest.raises(RequestValidationError):
        resolve_params(handler, [], {}, {}, None)


def test_resolve_invalid_json_body_422() -> None:
    def handler(item: ItemCreate) -> None:
        pass

    with pytest.raises(RequestValidationError):
        resolve_params(handler, [], {}, {}, b"not json")


def test_resolve_bool_conversion() -> None:
    def handler(active: bool = False) -> None:
        pass

    kwargs = resolve_params(handler, [], {}, {"active": "true"}, None)
    assert kwargs == {"active": True}