"""用户端点：获取当前用户信息、按 ID 查询用户。"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.security import get_current_active_user
from ....db.session import get_session
from ....models.user import User
from ....schemas.user import UserRead
from ....services.user_service import UserService

router = APIRouter()


@router.get("/me", response_model=UserRead)
async def read_current_user(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> UserRead:
    """获取当前登录用户信息。"""
    return UserRead.model_validate(current_user)


@router.get("/{user_id}", response_model=UserRead)
async def read_user(
    user_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> UserRead:
    """按 ID 查询用户公开信息。"""
    service = UserService(session)
    user = await service.get_by_id(user_id)
    return UserRead.model_validate(user)
