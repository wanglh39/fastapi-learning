"""异步数据库会话管理。

- create_async_engine（连接池）
- async_sessionmaker
- get_session() 依赖，供 Depends 注入
- lifespan 中管理 engine 生命周期
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from ..core.config import settings

engine = create_async_engine(
    settings.database_url,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    echo=False,
)
async_session_factory = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依赖：提供数据库会话，请求结束自动关闭。

    用法：
        async def list_items(session: AsyncSession = Depends(get_session)): ...
    """
    async with async_session_factory() as session:
        yield session


async def create_tables() -> None:
    """开发用：启动时自动建表。生产环境应使用 Alembic 迁移。"""
    from ..db.base import Base  # noqa: PLC0415
    from ..models import Article, Tag, User  # noqa: F401, PLC0415

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def dispose_engine() -> None:
    """关闭数据库连接池。"""
    await engine.dispose()
