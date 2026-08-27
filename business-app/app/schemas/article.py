"""Article 相关契约：创建、更新、响应、分页。

阶段 8.2 实现：ArticleCreate / ArticleUpdate / ArticleRead / Page。
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ArticleCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    content: str


class ArticleUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    content: str | None = None


class ArticleRead(BaseModel):
    id: int
    title: str
    content: str
    author_id: int
    created_at: datetime
    updated_at: datetime