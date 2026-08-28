"""文章端点：CRUD + 分页 + 标签关联。

- GET    /          分页列表
- POST   /          创建（需登录）
- GET    /{id}      详情
- PUT    /{id}      更新（仅作者）
- DELETE /{id}      删除（仅作者）
"""

from __future__ import annotations

import math
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.security import get_current_active_user
from ....db.session import get_session
from ....models.user import User
from ....schemas.article import ArticleCreate, ArticleRead, ArticleUpdate, Page
from ....services.article_service import ArticleService

router = APIRouter()


@router.get("/", response_model=Page[ArticleRead])
async def list_articles(
    session: Annotated[AsyncSession, Depends(get_session)],
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
) -> Page[ArticleRead]:
    """分页查询文章列表。"""
    service = ArticleService(session)
    items, total = await service.list(page=page, size=size)
    return Page(
        items=[ArticleRead.model_validate(a) for a in items],
        total=total,
        page=page,
        size=size,
        pages=math.ceil(total / size) if size > 0 else 0,
    )


@router.post("/", response_model=ArticleRead, status_code=201)
async def create_article(
    data: ArticleCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> ArticleRead:
    """创建文章（需登录）。"""
    service = ArticleService(session)
    article = await service.create(data, current_user)
    return ArticleRead.model_validate(article)


@router.get("/{article_id}", response_model=ArticleRead)
async def read_article(
    article_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ArticleRead:
    """查询文章详情。"""
    service = ArticleService(session)
    article = await service.get_by_id(article_id)
    return ArticleRead.model_validate(article)


@router.put("/{article_id}", response_model=ArticleRead)
async def update_article(
    article_id: int,
    data: ArticleUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> ArticleRead:
    """更新文章（仅作者可改）。"""
    service = ArticleService(session)
    article = await service.update(article_id, data, current_user)
    return ArticleRead.model_validate(article)


@router.delete("/{article_id}", status_code=204)
async def delete_article(
    article_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> None:
    """删除文章（仅作者可删）。"""
    service = ArticleService(session)
    await service.delete(article_id, current_user)
