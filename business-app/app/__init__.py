"""business-app: FastAPI 博客 API 业务实践项目。

分层架构（请求流向）：
    api (路由/契约) → service (业务逻辑) → repository (数据访问) → model (ORM)

目录结构：
    app/
    ├── core/           # 配置、安全、日志等基础设施
    ├── db/             # 数据库连接与会话
    ├── models/         # SQLAlchemy ORM 模型
    ├── schemas/        # Pydantic 请求/响应契约
    ├── api/v1/         # API 路由（按版本分组）
    ├── services/       # 业务逻辑层
    ├── repositories/   # 数据访问层
    └── main.py         # 应用入口
"""