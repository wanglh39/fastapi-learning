"""Article 与 Tag ORM 模型，及多对多关联表。

Article：id / title / content / author_id / created_at / updated_at。
Tag：id / name（唯一）。
article_tag：多对多关联。
"""

from __future__ import annotations

from sqlalchemy import Column, ForeignKey, Integer, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.base import Base, TimestampMixin

article_tag = Table(
    "article_tag",
    Base.metadata,
    Column("article_id", Integer, ForeignKey("articles.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class Article(Base, TimestampMixin):
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    content: Mapped[str] = mapped_column(Text)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))

    author: Mapped["User"] = relationship(back_populates="articles")
    tags: Mapped[list["Tag"]] = relationship(
        secondary=article_tag, back_populates="articles", lazy="selectin"
    )


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)

    articles: Mapped[list["Article"]] = relationship(
        secondary=article_tag, back_populates="tags", lazy="selectin"
    )
