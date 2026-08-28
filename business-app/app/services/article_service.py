"""文章业务逻辑层。

编排文章 CRUD 与权限校验，调用 ArticleRepository / TagRepository。
仅作者本人可修改/删除自己的文章。
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.exceptions import NotFoundError, PermissionDeniedError
from ..models.article import Article
from ..models.user import User
from ..repositories.article_repository import ArticleRepository, TagRepository
from ..schemas.article import ArticleCreate, ArticleUpdate


class ArticleService:
    """文章业务服务。"""

    def __init__(self, session: AsyncSession) -> None:
        self._article_repo = ArticleRepository(session)
        self._tag_repo = TagRepository(session)
        self._session = session

    async def create(self, data: ArticleCreate, author: User) -> Article:
        """创建文章，关联标签。"""
        tags = await self._tag_repo.get_by_ids(data.tag_ids) if data.tag_ids else []
        article = await self._article_repo.create(
            title=data.title, content=data.content, author_id=author.id, tags=tags
        )
        await self._session.commit()
        return article

    async def get_by_id(self, article_id: int) -> Article:
        """查询文章，不存在则抛 NotFoundError。"""
        article = await self._article_repo.get_by_id(article_id)
        if article is None:
            raise NotFoundError("文章", article_id)
        return article

    async def list(
        self, page: int = 1, size: int = 20, author_id: int | None = None
    ) -> tuple[list[Article], int]:
        """分页查询文章列表。"""
        return await self._article_repo.list(page=page, size=size, author_id=author_id)

    async def update(self, article_id: int, data: ArticleUpdate, user: User) -> Article:
        """更新文章（仅作者可改）。"""
        article = await self.get_by_id(article_id)
        if article.author_id != user.id:
            raise PermissionDeniedError("只能修改自己的文章")
        fields: dict[str, object] = {}
        if data.title is not None:
            fields["title"] = data.title
        if data.content is not None:
            fields["content"] = data.content
        if data.tag_ids is not None:
            fields["tags"] = await self._tag_repo.get_by_ids(data.tag_ids)
        article = await self._article_repo.update(article, **fields)
        await self._session.commit()
        return article

    async def delete(self, article_id: int, user: User) -> None:
        """删除文章（仅作者可删）。"""
        article = await self.get_by_id(article_id)
        if article.author_id != user.id:
            raise PermissionDeniedError("只能删除自己的文章")
        await self._article_repo.delete(article)
        await self._session.commit()
