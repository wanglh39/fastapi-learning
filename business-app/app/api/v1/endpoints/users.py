"""用户端点：查询、更新、禁用。

阶段 8.3 实现，受权限控制。
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()