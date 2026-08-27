"""认证端点：登录、注册、刷新 token。

阶段 8.3 实现 OAuth2 Password Flow + JWT。
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()