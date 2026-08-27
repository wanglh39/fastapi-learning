"""v1 路由聚合：挂载各资源端点。

阶段 8 实现：将 auth/users/articles 端点挂到 api_router，再由 main.py 加前缀。
"""

from __future__ import annotations

from fastapi import APIRouter

api_router = APIRouter()

# 阶段 8 启用：
# from .endpoints import auth, users, articles
# api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
# api_router.include_router(users.router, prefix="/users", tags=["users"])
# api_router.include_router(articles.router, prefix="/articles", tags=["articles"])