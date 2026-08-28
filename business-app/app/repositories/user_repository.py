"""用户数据访问层。

封装 SQLAlchemy 查询，向上层返回 User ORM 对象，屏蔽查询细节。
所有方法均为 async，接收 AsyncSession。
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.user import User


class UserRepository:
    """User 数据访问对象。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: int) -> User | None:
        """按主键查询用户。"""
        return await self._session.get(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        """按 email 查询用户（用于登录与注册查重）。"""
        stmt = select(User).where(User.email == email)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, email: str, hashed_password: str) -> User:
        """创建用户并刷新到数据库，返回含 id 的 User。"""
        user = User(email=email, hashed_password=hashed_password)
        self._session.add(user)
        await self._session.flush()
        await self._session.refresh(user)
        return user

    async def list(self, page: int = 1, size: int = 20) -> tuple[list[User], int]:
        """分页查询用户列表，返回 (items, total)。"""
        offset = (page - 1) * size
        total_stmt = select(func.count()).select_from(User)
        total = (await self._session.execute(total_stmt)).scalar_one()
        items_stmt = select(User).offset(offset).limit(size).order_by(User.id)
        items = list((await self._session.execute(items_stmt)).scalars().all())
        return items, total

    async def update_active(self, user_id: int, is_active: bool) -> User | None:
        """更新用户激活状态。"""
        user = await self.get_by_id(user_id)
        if user is None:
            return None
        user.is_active = is_active
        await self._session.flush()
        return user
