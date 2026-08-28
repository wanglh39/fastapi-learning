"""SQLAlchemy 声明基类与公共 mixin。

提供 DeclarativeBase 和 TimestampMixin（created_at / updated_at 自动维护）。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """所有 ORM 模型的基类。"""


class TimestampMixin:
    """为模型注入 created_at / updated_at 时间戳列。

    - created_at：插入时由数据库 server_default 自动填充。
    - updated_at：插入时填充，每次 UPDATE 由 onupdate 自动刷新。
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
