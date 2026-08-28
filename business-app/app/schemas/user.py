"""User 相关契约：注册、登录、响应、Token。

所有契约继承 pydantic BaseModel，自动参与 OpenAPI 文档生成。
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    """注册请求。"""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserLogin(BaseModel):
    """登录请求。"""

    email: EmailStr
    password: str


class UserRead(BaseModel):
    """用户响应（不含密码）。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    is_active: bool
    is_superuser: bool
    created_at: datetime


class Token(BaseModel):
    """登录成功返回的 access token。"""

    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """JWT payload 解析结果。"""

    sub: str | None = None
    exp: int | None = None
