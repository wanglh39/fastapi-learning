"""文章与标签数据访问层。

封装 Article / Tag 的 CRUD 与分页查询。
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.article import Article, Tag
from ..models.user import User


class ArticleRepository:
    """Article 数据访问对象。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, article_id: int) -> Article | None:
        """按主键查询文章（含标签 selectin 加载）。"""
        return await self._session.get(Article, article_id)

    async def create(
        self, title: str, content: str, author_id: int, tags: list[Tag] | None = None
    ) -> Article:
        """创建文章并关联标签。"""
        article = Article(title=title, content=content, author_id=author_id)
        if tags:
            article.tags = tags
        self._session.add(article)
        await self._session.flush()
        await self._session.refresh(article)
        return article

    async def update(self, article: Article, **fields: object) -> Article:
        """部分更新文章字段。"""
        for key, value in fields.items():
            setattr(article, key, value)
        await self._session.flush()
        await self._session.refresh(article)
        return article

    async def delete(self, article: Article) -> None:
        """删除文章。"""
        await self._session.delete(article)
        await self._session.flush()

    async def list(
        self,
        page: int = 1,
        size: int = 20,
        author_id: int | None = None,
    ) -> tuple[list[Article], int]:
        """分页查询文章列表，可按作者过滤。返回 (items, total)。"""
        offset = (page - 1) * size
        base = select(Article)
        count_base = select(func.count()).select_from(Article)
        if author_id is not None:
            base = base.where(Article.author_id == author_id)
            count_base = count_base.where(Article.author_id == author_id)
        total = (await self._session.execute(count_base)).scalar_one()
        stmt = base.offset(offset).limit(size).order_by(Article.created_at.desc())
        items = list((await self._session.execute(stmt)).scalars().all())
        return items, total


class TagRepository:
    """Tag 数据访问对象。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_or_create(self, name: str) -> Tag:
        """按名称查找标签，不存在则创建。"""
        stmt = select(Tag).where(Tag.name == name)
        tag = (await self._session.execute(stmt)).scalar_one_or_none()
        if tag is None:
            tag = Tag(name=name)
            self._session.add(tag)
            await self._session.flush()
            await self._session.refresh(tag)
        return tag

    async def get_by_ids(self, tag_ids: list[int]) -> list[Tag]:
        """按 ID 列表批量查询标签。"""
        if not tag_ids:
            return []
        stmt = select(Tag).where(Tag.id.in_(tag_ids))
        return list((await self._session.execute(stmt)).scalars().all())

    async def list(self) -> list[Tag]:
        """查询全部标签。"""
        stmt = select(Tag).order_by(Tag.name)
        return list((await self._session.execute(stmt)).scalars().all())
