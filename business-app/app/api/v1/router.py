"""v1 路由聚合：挂载各资源端点。"""

from __future__ import annotations

from fastapi import APIRouter

from .endpoints import articles, auth, users

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(articles.router, prefix="/articles", tags=["articles"])
