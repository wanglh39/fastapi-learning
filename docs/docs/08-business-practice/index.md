# 阶段 8 · 业务工程化实践

!!! info "本章定位"
    用官方 FastAPI 做一个规范化的博客 API（用户/权限/文章/标签），覆盖工程化最佳实践。此时你对框架内部已有"上帝视角"，写出的代码质量完全不同。

---

## 本章学习目标

读完本章后，你应当能够：

1. 设计合理的分层项目结构（api → service → repository → model）
2. 用 pydantic-settings 管理多环境配置
3. 集成 SQLAlchemy 2.0 async + Alembic 迁移
4. 实现 OAuth2 + JWT 认证与 RBAC 权限
5. 设计统一错误响应与结构化日志（trace_id 贯穿）
6. 管理 API 版本
7. 编写 pytest + httpx + testcontainers 测试
8. 完成可部署的工程化项目

---

## 小节目录

1. [8.1 项目结构与分层](#81-项目结构与分层)
2. [8.2 配置管理](#82-配置管理)
3. [8.3 数据库集成](#83-数据库集成)
4. [8.4 认证与权限](#84-认证与权限)
5. [8.5 错误处理与日志](#85-错误处理与日志)
6. [8.6 API 版本管理](#86-api-版本管理)
7. [8.7 测试策略](#87-测试策略)
8. [8.8 性能优化](#88-性能优化)
9. [实践任务与产出](#实践任务与产出)
10. [小结与下一章衔接](#小结与下一章衔接)

---

## 8.1 项目结构与分层

### 8.1.1 分层架构

```
api (路由/契约) → service (业务逻辑) → repository (数据访问) → model (ORM)
```

待补充：讲每层职责与禁止跨层调用的规则，为什么这样分（可测试性、可替换性、关注点分离）。

### 8.1.2 目录组织

待补充：对照 `business-app/app/` 的实际目录，讲每个子包的职责。

### 8.1.3 APIRouter 组织

待补充：按业务域拆分 router，`include_router` 聚合，prefix/tags 组织文档。

---

## 8.2 配置管理

### 8.2.1 pydantic-settings

待补充：`BaseSettings` 从环境变量/.env 加载，类型校验，敏感配置不入库。

### 8.2.2 多环境

待补充：`.env.dev` / `.env.prod` / `.env.test` 切换，`SettingsConfigDict` 配置。

---

## 8.3 数据库集成

### 8.3.1 SQLAlchemy 2.0 async

待补充：`create_async_engine`、`async_sessionmaker`、`DeclarativeBase`、`Mapped`/`mapped_column` 新语法。

### 8.3.2 会话注入

待补充：`get_session` 依赖用 `yield`，请求结束自动关闭。

### 8.3.3 Alembic 迁移

待补充：`alembic init -t async`、配置 env.py 用 async engine、生成与执行迁移。

### 8.3.4 仓储模式

待补充：`UserRepository` 封装查询，service 不直接写 ORM，便于单测 mock。

---

## 8.4 认证与权限

### 8.4.1 OAuth2 Password Flow

待补充：`OAuth2PasswordBearer` 的 tokenUrl、登录端点签发 JWT。

### 8.4.2 JWT 签发与校验

待补充：`python-jose` 签发 access token、`Depends(get_current_user)` 解析与注入。

### 8.4.3 密码哈希

待补充：`passlib` bcrypt，`verify_password` / `hash_password`。

### 8.4.4 RBAC 权限

待补充：角色字段 + 权限装饰器/依赖（`require_role("admin")`），或 Casbin 引入时机。

---

## 8.5 错误处理与日志

### 8.5.1 统一响应封装

待补充：`{code, message, data}` 统一结构，成功与错误的格式一致性。

### 8.5.2 全局异常处理器

待补充：`@app.exception_handler` 注册业务异常 → HTTP 响应映射，422/401/403/404 的统一处理。

### 8.5.3 结构化日志

待补充：`structlog` 配置，JSON 输出（生产）/ 彩色控制台（开发），中间件注入 trace_id 到 context，日志自动携带 trace_id。

---

## 8.6 API 版本管理

待补充：URL 前缀法（`/api/v1`、`/api/v2`）最实用；对比 Header 法、Accept header 法的取舍；多版本共存期的路由组织。

---

## 8.7 测试策略

### 8.7.1 单元测试

待补充：service 层用 mock repository 单测，纯业务逻辑不碰 DB。

### 8.7.2 集成测试

待补充：`httpx.AsyncClient` 直传 ASGI（不起真实服务），`testcontainers` 起真实 Postgres，fixture 管理 session 与测试用户。

### 8.7.3 镜像目录结构

待补充：`tests/api/v1/endpoints/test_articles.py` 对应 `app/api/v1/endpoints/articles.py`，遵循项目所有规范。

---

## 8.8 性能优化

待补充：uvicorn workers、gunicorn 进程管理、连接池调优、`fastapi-cache2` 响应缓存、N+1 查询检测、预热。

---

## 实践任务与产出

### 任务：完整博客 API

实现用户注册登录、文章 CRUD（仅作者可改）、标签关联、分页查询，覆盖认证/权限/错误/日志/测试。

### 产出

- `business-app` 完整可部署项目
- 每个子主题一篇笔记（合计 ≥ 700 行）

---

## 小结与下一章衔接

本章完成业务实战。下一章沉淀为文档站并部署上线。

---

!!! todo "待填充标记说明"
    本文件为大纲骨架，标注「待补充」处为后续要展开的内容点。每个待补充点都已规划好要讲的核心问题与示例方向，填充时直接展开即可达到 ≥ 700 行深度。**笔记深度与数量只增不减**，本骨架的小节结构在填充时只会扩充不会删减。