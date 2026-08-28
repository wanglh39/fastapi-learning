"""Article 与 Tag 相关契约：创建、更新、响应、分页。

分页响应 Page[T] 使用 Pydantic 泛型，适配任意资源类型。
"""

from __future__ import annotations

from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field


class TagCreate(BaseModel):
    """创建标签。"""

    name: str = Field(min_length=1, max_length=100)


class TagRead(BaseModel):
    """标签响应。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class ArticleCreate(BaseModel):
    """创建文章请求。tag_ids 可选，关联已有标签。"""

    title: str = Field(min_length=1, max_length=255)
    content: str
    tag_ids: list[int] = Field(default_factory=list)


class ArticleUpdate(BaseModel):
    """更新文章请求。所有字段可选，部分更新。"""

    title: str | None = Field(default=None, min_length=1, max_length=255)
    content: str | None = None
    tag_ids: list[int] | None = None


class ArticleRead(BaseModel):
    """文章响应（含标签列表）。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    content: str
    author_id: int
    created_at: datetime
    updated_at: datetime
    tags: list[TagRead] = Field(default_factory=list)


T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    """分页响应泛型包装。"""

    items: list[T]
    total: int
    page: int
    size: int
    pages: int
