"""Pydantic v2 核心能力演示。

运行：
    uv run python examples/pydantic_demo.py

覆盖：BaseModel 定义/实例化、自动类型转换、验证失败、嵌套模型、
Field 约束、验证器、序列化、JSON Schema 生成、Annotated 用法。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, TypedDict

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator


def section(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


# ---------- 1. BaseModel 定义与实例化 ----------

class User(BaseModel):
    id: int
    name: str
    email: str
    age: int = 0


def demo_basic() -> None:
    section("1. BaseModel 定义与实例化")
    user = User(id=1, name="alice", email="a@x.com", age=30)
    print(f"实例化成功: {user}")
    print(f"id 类型: {type(user.id).__name__}")

    auto_converted = User(id="42", name="bob", email="b@x.com")
    print(f"\n自动类型转换: id='42' (str) → {auto_converted.id} ({type(auto_converted.id).__name__})")


# ---------- 2. 验证失败 ----------

def demo_validation_error() -> None:
    section("2. 验证失败")
    try:
        User(id="not-a-number", name="x", email="x@x.com")
    except ValidationError as exc:
        print(f"ValidationError 抛出:")
        for err in exc.errors():
            print(f"  位置: {err['loc']}  类型: {err['type']}  信息: {err['msg']}")


# ---------- 3. 嵌套模型 ----------

class Address(BaseModel):
    city: str
    zip_code: str


class UserWithAddress(BaseModel):
    id: int
    name: str
    address: Address


def demo_nested() -> None:
    section("3. 嵌套模型")
    user = UserWithAddress(
        id=1,
        name="alice",
        address={"city": "北京", "zip_code": "100000"},
    )
    print(f"嵌套实例化: {user}")
    print(f"address 类型: {type(user.address).__name__}, city: {user.address.city}")


# ---------- 4. Field 约束 ----------

class Product(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    price: float = Field(gt=0, description="价格必须为正")
    stock: int = Field(ge=0, default=0)
    tags: list[str] = Field(default_factory=list, max_length=10)


def demo_field_constraints() -> None:
    section("4. Field 约束")
    product = Product(name="Widget", price=9.99, stock=100, tags=["tool", "new"])
    print(f"合法产品: {product}")

    try:
        Product(name="", price=-1, stock=-5)
    except ValidationError as exc:
        print(f"\n约束违反:")
        for err in exc.errors():
            print(f"  {err['loc']}: {err['msg']}")


# ---------- 5. 验证器 ----------

class SignupRequest(BaseModel):
    password: str
    password_confirm: str

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("密码至少 8 位")
        return v

    @model_validator(mode="after")
    def passwords_match(self) -> "SignupRequest":
        if self.password != self.password_confirm:
            raise ValueError("两次密码不一致")
        return self


def demo_validators() -> None:
    section("5. 验证器: field_validator + model_validator")
    req = SignupRequest(password="secure123", password_confirm="secure123")
    print(f"验证通过: {req}")

    try:
        SignupRequest(password="short", password_confirm="short")
    except ValidationError as exc:
        print(f"\nfield_validator 拦截: {exc.errors()[0]['msg']}")

    try:
        SignupRequest(password="secure123", password_confirm="different")
    except ValidationError as exc:
        print(f"model_validator 拦截: {exc.errors()[0]['msg']}")


# ---------- 6. 序列化 ----------

def demo_serialization() -> None:
    section("6. 序列化: model_dump / model_dump_json")
    user = User(id=1, name="alice", email="a@x.com", age=30)

    print(f"model_dump():       {user.model_dump()}")
    print(f"model_dump_json():  {user.model_dump_json()}")
    print(f"排除 age:           {user.model_dump(exclude={'age'})}")
    print(f"仅含 name,email:    {user.model_dump(include={'name', 'email'})}")


# ---------- 7. JSON Schema 生成 ----------

def demo_json_schema() -> None:
    section("7. JSON Schema 自动生成 (FastAPI 自动文档的源头)")
    schema = User.model_json_schema()
    print(f"User.schema:")
    for key, value in schema.items():
        print(f"  {key}: {value}")

    print(f"\nProduct.schema (含约束):")
    product_schema = Product.model_json_schema()
    import json
    print(json.dumps(product_schema, indent=2, ensure_ascii=False))


# ---------- 8. Annotated + Field ----------

Quantity = Annotated[int, Field(gt=0, le=100, description="数量 1-100")]


class Order(BaseModel):
    product_id: int
    quantity: Quantity


def demo_annotated() -> None:
    section("8. Annotated + Field (PEP 593, FastAPI 推崇)")
    order = Order(product_id=1, quantity=50)
    print(f"合法: {order}")

    try:
        Order(product_id=1, quantity=0)
    except ValidationError as exc:
        print(f"quantity=0 违反 gt=0: {exc.errors()[0]['msg']}")

    try:
        Order(product_id=1, quantity=200)
    except ValidationError as exc:
        print(f"quantity=200 违反 le=100: {exc.errors()[0]['msg']}")


# ---------- 9. dataclass / TypedDict / BaseModel 对比 ----------

@dataclass
class UserDataclass:
    id: int
    name: str


class UserTypedDict(TypedDict):
    id: int
    name: str


def demo_comparison() -> None:
    section("9. dataclass / TypedDict / BaseModel 对比")

    dc = UserDataclass(id="42", name="alice")
    print(f"dataclass: id='42' → {dc.id} ({type(dc.id).__name__}) — 无运行时验证!")

    td: UserTypedDict = {"id": "not-int", "name": "alice"}
    print(f"TypedDict: id='not-int' — 无运行时验证!")

    try:
        User(id="not-int", name="alice")
    except ValidationError:
        print(f"BaseModel: id='not-int' — ValidationError 抛出, 有运行时验证!")


def main() -> None:
    demo_basic()
    demo_validation_error()
    demo_nested()
    demo_field_constraints()
    demo_validators()
    demo_serialization()
    demo_json_schema()
    demo_annotated()
    demo_comparison()
    print("\n完成。")


if __name__ == "__main__":
    main()