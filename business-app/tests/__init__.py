"""测试包。

镜像 app/ 目录结构：
    tests/api/v1/endpoints/test_articles.py  ←  app/api/v1/endpoints/articles.py

阶段 8.6 实现：
- conftest.py 提供 async client、测试 DB session、测试用户 fixture
- httpx.AsyncClient 直传 ASGI，不起真实服务
- testcontainers 起真实 Postgres 做集成测试
"""