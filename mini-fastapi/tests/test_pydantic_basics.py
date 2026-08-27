"""Pydantic v2 基础行为测试。

验证阶段 2 学习的 Pydantic 核心能力：类型转换、验证、约束、序列化、Schema。
"""

from __future__ import annotations

from typing import Annotated, Optional

import pytest
from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator


class User(BaseModel):
    id: int
    name: str
    age: int = 0


class Product(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    price: float = Field(gt=0)
    stock: int = Field(ge=0, default=0)


class Address(BaseModel):
    city: str


class UserWithAddress(BaseModel):
    id: int
    address: Address


Quantity = Annotated[int, Field(gt=0, le=100)]


class Order(BaseModel):
    quantity: Quantity


class Signup(BaseModel):
    password: str
    confirm: str

    @field_validator("password")
    @classmethod
    def strong(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("密码至少 8 位")
        return v

    @model_validator(mode="after")
    def match(self) -> "Signup":
        if self.password != self.confirm:
            raise ValueError("密码不一致")
        return self


def test_type_coercion_str_to_int() -> None:
    user = User(id="42", name="alice")
    assert user.id == 42
    assert isinstance(user.id, int)


def test_validation_error_on_invalid_type() -> None:
    with pytest.raises(ValidationError) as exc_info:
        User(id="not-a-number", name="x")
    errors = exc_info.value.errors()
    assert errors[0]["loc"] == ("id",)


def test_field_constraints_gt() -> None:
    with pytest.raises(ValidationError):
        Product(name="ok", price=-1)


def test_field_constraints_min_length() -> None:
    with pytest.raises(ValidationError):
        Product(name="", price=1)


def test_field_constraints_ge_zero() -> None:
    with pytest.raises(ValidationError):
        Product(name="ok", price=1, stock=-1)


def test_nested_model_validation() -> None:
    user = UserWithAddress(id=1, address={"city": "北京"})
    assert user.address.city == "北京"
    assert isinstance(user.address, Address)


def test_serialization_model_dump() -> None:
    user = User(id=1, name="alice", age=30)
    assert user.model_dump() == {"id": 1, "name": "alice", "age": 30}


def test_serialization_exclude() -> None:
    user = User(id=1, name="alice", age=30)
    assert user.model_dump(exclude={"age"}) == {"id": 1, "name": "alice"}


def test_json_schema_has_properties() -> None:
    schema = User.model_json_schema()
    assert schema["type"] == "object"
    assert "id" in schema["properties"]
    assert "name" in schema["properties"]
    assert schema["required"] == ["id", "name"]


def test_json_schema_field_constraints() -> None:
    schema = Product.model_json_schema()
    price_schema = schema["properties"]["price"]
    assert price_schema["exclusiveMinimum"] == 0


def test_annotated_field_validation() -> None:
    Order(quantity=50)
    with pytest.raises(ValidationError):
        Order(quantity=0)
    with pytest.raises(ValidationError):
        Order(quantity=200)


def test_field_validator_intercepts() -> None:
    with pytest.raises(ValidationError) as exc_info:
        Signup(password="short", confirm="short")
    assert "至少 8 位" in exc_info.value.errors()[0]["msg"]


def test_model_validator_intercepts() -> None:
    with pytest.raises(ValidationError) as exc_info:
        Signup(password="secure123", confirm="different")
    assert "不一致" in exc_info.value.errors()[0]["msg"]


def test_model_validate_from_dict() -> None:
    user = User.model_validate({"id": 1, "name": "alice"})
    assert user.name == "alice"


def test_optional_field_allows_none() -> None:

    class Query(BaseModel):
        q: Optional[str] = None

    assert Query().q is None
    assert Query(q="hello").q == "hello"