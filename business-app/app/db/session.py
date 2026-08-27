"""异步数据库会话管理。

阶段 8.2 实现：
- create_async_engine（连接池）
- async_sessionmaker
- get_session() 依赖，供 Depends 注入
- lifespan 中管理 engine 生命周期
"""

from __future__ import annotations

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from ..core.config import settings

engine = create_async_engine(settings.database_url, pool_size=settings.db_pool_size, max_overflow=settings.db_max_overflow)
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依赖：提供数据库会话，请求结束自动关闭。

    用法：
        async def list_items(session: AsyncSession = Depends(get_session)): ...
    """
    async with async_session_factory() as session:
        yield session