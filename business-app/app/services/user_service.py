"""用户业务逻辑层。

编排注册、认证等业务规则，调用 UserRepository 与 security 模块。
不直接接触 ORM 查询细节。
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.exceptions import ConflictError, NotFoundError
from ..core.security import hash_password, verify_password
from ..models.user import User
from ..repositories.user_repository import UserRepository
from ..schemas.user import UserCreate


class UserService:
    """用户业务服务。"""

    def __init__(self, session: AsyncSession) -> None:
        self._repo = UserRepository(session)
        self._session = session

    async def register(self, data: UserCreate) -> User:
        """注册新用户。

        - 检查邮箱是否已注册（冲突则抛 ConflictError）
        - 哈希密码后持久化
        """
        existing = await self._repo.get_by_email(data.email)
        if existing is not None:
            raise ConflictError(f"邮箱 {data.email} 已注册")
        hashed = hash_password(data.password)
        user = await self._repo.create(email=data.email, hashed_password=hashed)
        await self._session.commit()
        return user

    async def authenticate(self, email: str, password: str) -> User:
        """校验邮箱+密码，返回用户或 None。"""
        user = await self._repo.get_by_email(email)
        if user is None or not verify_password(password, user.hashed_password):
            return None
        if not user.is_active:
            return None
        return user

    async def get_by_id(self, user_id: int) -> User:
        """按 ID 查询用户，不存在则抛 NotFoundError。"""
        user = await self._repo.get_by_id(user_id)
        if user is None:
            raise NotFoundError("用户", user_id)
        return user
