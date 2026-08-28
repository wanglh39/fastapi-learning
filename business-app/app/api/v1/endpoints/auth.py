"""认证端点：注册、登录。

- POST /register：注册新用户
- POST /login：OAuth2 Password Flow，返回 JWT
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.security import create_access_token
from ....db.session import get_session
from ....schemas.user import Token, UserCreate, UserRead
from ....services.user_service import UserService

router = APIRouter()


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(
    data: UserCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> UserRead:
    """注册新用户。"""
    service = UserService(session)
    user = await service.register(data)
    return UserRead.model_validate(user)


@router.post("/login", response_model=Token)
async def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Token:
    """OAuth2 Password Flow 登录，返回 access token。"""
    service = UserService(session)
    user = await service.authenticate(form.username, form.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(subject=user.email)
    return Token(access_token=token)
