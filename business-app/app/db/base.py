"""SQLAlchemy 声明基类。

阶段 8.2 实现：DeclarativeBase + 公共字段 mixin（id/created_at/updated_at）。
"""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """所有 ORM 模型的基类。"""