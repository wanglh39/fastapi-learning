# 阶段 8 · 业务工程化实践

!!! info "本章定位"
    用官方 FastAPI 做一个规范化的博客 API（用户/权限/文章/标签），覆盖工程化最佳实践。此时你对框架内部已有"上帝视角"，写出的代码质量完全不同。

    本章所有代码都在 `business-app/` 目录中，30 个测试全部通过。读者可对照源码阅读。

---

## 本章学习目标

读完本章后，你应当能够：

1. 设计合理的分层项目结构（api → service → repository → model）
2. 用 pydantic-settings 管理多环境配置
3. 集成 SQLAlchemy 2.0 async + Alembic 迁移
4. 实现 OAuth2 + JWT 认证与 RBAC 权限
5. 设计统一错误响应与结构化日志（trace_id 贯穿）
6. 管理 API 版本
7. 编写 pytest + httpx 测试
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

### 8.1.1 为什么需要分层

在阶段 1-7 中，我们造轮子时把路由、业务逻辑、数据访问全写在一个函数里。这对小项目没问题，但业务项目一旦复杂，所有代码混在一起会导致：

- **不可测试**：业务逻辑耦合了 HTTP 和数据库，单测要起真实服务
- **不可替换**：换数据库要改业务代码，换 ORM 要改路由代码
- **不可协作**：多人改同一个文件，冲突频繁

分层架构的核心思想是**关注点分离**（Separation of Concerns）：

```
请求 → api (路由/契约) → service (业务逻辑) → repository (数据访问) → model (ORM)
                                                                                    ↓
响应 ← api (序列化) ← service (返回领域对象) ← repository (返回 ORM 对象) ← model (持久化)
```

每层有明确职责：

| 层 | 职责 | 禁止 |
|---|---|---|
| **api** | 接收请求、校验入参、调用 service、序列化响应 | 不碰 ORM 查询 |
| **service** | 编排业务规则、调用 repository、权限校验 | 不写 SQL/select 语句 |
| **repository** | 封装 SQLAlchemy 查询、返回 ORM 对象 | 不含业务规则 |
| **model** | 定义表结构、关系 | 不含业务逻辑 |

### 8.1.2 目录组织

我们的 `business-app/` 目录结构：

```
business-app/
├── pyproject.toml          # 依赖与工具配置
├── .env.example            # 环境变量模板
├── app/
│   ├── __init__.py         # 包文档
│   ├── main.py             # 应用工厂 create_app()
│   ├── core/               # 基础设施
│   │   ├── config.py       # pydantic-settings 配置
│   │   ├── security.py     # JWT + 密码哈希 + 依赖注入
│   │   ├── logging.py      # structlog 配置
│   │   └── exceptions.py   # 业务异常定义
│   ├── db/                 # 数据库基础设施
│   │   ├── base.py         # DeclarativeBase + TimestampMixin
│   │   └── session.py      # engine + get_session 依赖
│   ├── models/             # ORM 模型
│   │   ├── user.py         # User 表
│   │   └── article.py      # Article + Tag + article_tag 关联表
│   ├── schemas/            # Pydantic 契约
│   │   ├── user.py         # UserCreate/UserRead/Token
│   │   └── article.py      # ArticleCreate/ArticleRead/Page
│   ├── repositories/       # 数据访问层
│   │   ├── user_repository.py
│   │   └── article_repository.py
│   ├── services/           # 业务逻辑层
│   │   ├── user_service.py
│   │   └── article_service.py
│   └── api/                # API 路由
│       └── v1/
│           ├── router.py   # 聚合各资源端点
│           └── endpoints/
│               ├── auth.py
│               ├── users.py
│               └── articles.py
└── tests/                  # 测试（镜像 app 结构）
    ├── conftest.py
    ├── test_auth.py
    ├── test_users.py
    └── test_articles.py
```

### 8.1.3 APIRouter 组织

按业务域拆分 router，用 `include_router` 聚合：

```python
# app/api/v1/router.py
from fastapi import APIRouter
from .endpoints import articles, auth, users

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(articles.router, prefix="/articles", tags=["articles"])
```

在 `main.py` 中加版本前缀：

```python
app.include_router(api_router, prefix=settings.api_v1_prefix)  # /api/v1
```

这样 OpenAPI 文档自动按 tags 分组，URL 带版本号。

### 8.1.4 应用工厂模式

`create_app()` 工厂函数组装所有组件：

```python
# app/main.py（简化）
def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.add_middleware(CORSMiddleware, ...)
    app.add_middleware(TraceIdMiddleware)
    app.include_router(api_router, prefix=settings.api_v1_prefix)
    app.add_exception_handler(NotFoundError, _business_error_to_response)
    return app

app = create_app()
```

工厂模式的好处：

- **测试友好**：测试时可以创建不同配置的 app 实例
- **扩展性**：可以接受参数来切换中间件、路由、配置
- **生命周期清晰**：所有组件在一个函数里组装，一目了然

---

## 8.2 配置管理

### 8.2.1 pydantic-settings

生产应用的配置来源多样：环境变量、.env 文件、命令行参数。`pydantic-settings` 提供类型安全的配置管理：

```python
# app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "BlogAPI"
    app_version: str = "0.1.0"
    api_v1_prefix: str = "/api/v1"

    database_url: str = "sqlite+aiosqlite:///./blog.db"
    db_pool_size: int = 10
    db_max_overflow: int = 20

    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 30
    algorithm: str = "HS256"

    log_level: str = "INFO"

settings = Settings()
```

**关键设计**：

1. **类型校验**：`db_pool_size: int` 自动拒绝非数字值
2. **默认值**：开发时无需任何配置即可运行
3. **环境变量覆盖**：`DATABASE_URL=...` 自动映射到 `database_url`（大小写不敏感）
4. **.env 文件**：`env_file=".env"` 自动加载，不进 Git 仓库
5. **extra="ignore"**：忽略未定义的环境变量，避免报错

### 8.2.2 多环境

通过不同的 `.env` 文件切换环境：

```bash
# .env.dev
DATABASE_URL=sqlite+aiosqlite:///./blog_dev.db
LOG_LEVEL=DEBUG

# .env.prod
DATABASE_URL=postgresql+asyncpg://user:pass@db/blog
SECRET_KEY=a-very-long-random-string
LOG_LEVEL=INFO

# .env.test
DATABASE_URL=sqlite+aiosqlite://
```

启动时指定：

```bash
ENV_FILE=.env.prod uvicorn app.main:app
```

在 `Settings` 中添加 `env_file` 参数支持：

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=os.getenv("ENV_FILE", ".env"), ...)
```

### 8.2.3 敏感配置安全

- **SECRET_KEY**：生产环境必须替换为随机长字符串
- **数据库密码**：只放 .env，不进 Git
- **.env.example**：提供模板，不含真实值

```bash
# .env.example
APP_NAME=BlogAPI
DATABASE_URL=sqlite+aiosqlite:///./blog.db
SECRET_KEY=change-me-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=30
LOG_LEVEL=INFO
```

---

## 8.3 数据库集成

### 8.3.1 SQLAlchemy 2.0 async

SQLAlchemy 2.0 引入了全新的类型注解 API：

```python
# app/db/base.py
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    """所有 ORM 模型的基类。"""

class TimestampMixin:
    """自动维护 created_at / updated_at。"""
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
```

**新语法要点**：

- `Mapped[T]`：声明列类型，替代旧的 `Column(Integer)`
- `mapped_column()`：配置列属性（主键、索引、外键等）
- `server_default=func.now()`：数据库端默认值
- `onupdate=func.now()`：UPDATE 时自动刷新

### 8.3.2 模型定义与关系

```python
# app/models/user.py
class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)

    articles: Mapped[list["Article"]] = relationship(
        back_populates="author", cascade="all, delete-orphan"
    )
```

多对多关系通过关联表：

```python
# app/models/article.py
article_tag = Table(
    "article_tag", Base.metadata,
    Column("article_id", Integer, ForeignKey("articles.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)

class Article(Base, TimestampMixin):
    __tablename__ = "articles"
    # ...
    tags: Mapped[list["Tag"]] = relationship(
        secondary=article_tag, back_populates="articles", lazy="selectin"
    )
```

**`lazy="selectin"`**：加载文章时自动用 IN 查询加载标签，避免 N+1 问题。

### 8.3.3 异步引擎与会话注入

```python
# app/db/session.py
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

engine = create_async_engine(
    settings.database_url,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
)
async_session_factory = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session
```

**`expire_on_commit=False`**：commit 后不过期对象属性，避免异步上下文中触发懒加载报错。

在路由中通过 `Depends` 注入：

```python
async def list_articles(
    session: Annotated[AsyncSession, Depends(get_session)],
):
    ...
```

### 8.3.4 仓储模式

Repository 封装所有数据访问，Service 不直接写 SQL：

```python
# app/repositories/user_repository.py
class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, email: str, hashed_password: str) -> User:
        user = User(email=email, hashed_password=hashed_password)
        self._session.add(user)
        await self._session.flush()
        await self._session.refresh(user)
        return user
```

**好处**：

- Service 层可以 mock repository 做纯单测
- 查询逻辑集中一处，不散落在各路由
- 换数据库只需改 repository 实现

### 8.3.5 Alembic 迁移

生产环境不用 `create_all`，而是用 Alembic 管理表结构变更：

```bash
# 初始化（使用 async 模板）
alembic init -t async migrations

# 生成迁移
alembic revision --autogenerate -m "create users and articles"

# 执行迁移
alembic upgrade head
```

`alembic.ini` 配置数据库 URL，`env.py` 使用 async engine：

```python
# migrations/env.py（核心片段）
async def run_migrations_online():
    connectable = create_async_engine(config.get_main_option("sqlalchemy.url"))
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
```

---

## 8.4 认证与权限

### 8.4.1 OAuth2 Password Flow

OAuth2 Password Flow 是最常用的 API 认证方式：

1. 用户用 email + password 请求 `/auth/login`
2. 服务端校验后返回 JWT access token
3. 后续请求在 Header 中携带 `Authorization: Bearer <token>`
4. 服务端解析 token 获取用户身份

```python
# app/core/security.py
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_v1_prefix}/auth/login")
```

`OAuth2PasswordBearer` 做了两件事：

- 从 `Authorization: Bearer xxx` 提取 token
- 在 OpenAPI 文档中添加"Authorize"按钮

### 8.4.2 JWT 签发与校验

JWT（JSON Web Token）由 Header.Payload.Signature 组成：

```python
from jose import jwt

def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)

def decode_token(token: str) -> TokenData:
    payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    return TokenData(sub=payload.get("sub"), exp=payload.get("exp"))
```

**JWT 要点**：

- `sub`（subject）：存用户标识（email）
- `exp`（expiration）：过期时间，过期后自动拒绝
- `secret_key`：签名密钥，泄露=任何人可伪造 token
- 无状态：服务端不存 token，靠签名验证

### 8.4.3 密码哈希

使用 bcrypt 做密码哈希（不存明文）：

```python
import bcrypt

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
```

**bcrypt 特点**：

- 自带 salt（每次哈希结果不同）
- 计算慢（故意慢，抵抗暴力破解）
- 不可逆（只能验证，不能解密）

### 8.4.4 依赖注入获取当前用户

FastAPI 的依赖注入让认证极其简洁：

```python
async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> User:
    token_data = decode_token(token)
    repo = UserRepository(session)
    user = await repo.get_by_email(token_data.sub)
    if user is None:
        raise HTTPException(401, "无法验证凭据")
    return user

async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    if not current_user.is_active:
        raise HTTPException(403, "用户已被禁用")
    return current_user
```

路由中只需声明参数：

```python
@router.post("/")
async def create_article(
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    # current_user 一定是已登录且激活的用户
    ...
```

### 8.4.5 权限校验

业务级权限（如"只能改自己的文章"）放在 Service 层：

```python
# app/services/article_service.py
async def update(self, article_id: int, data: ArticleUpdate, user: User) -> Article:
    article = await self.get_by_id(article_id)
    if article.author_id != user.id:
        raise PermissionDeniedError("只能修改自己的文章")
    ...
```

**为什么放 Service 而不是路由**：

- 权限是业务规则，不是 HTTP 关注点
- 同一业务可能被多个入口调用（API、CLI、定时任务），权限一致
- 测试时直接测 service，不需要 HTTP 客户端

---

## 8.5 错误处理与日志

### 8.5.1 业务异常体系

定义业务异常类，携带语义信息：

```python
# app/core/exceptions.py
class BusinessError(Exception):
    def __init__(self, message: str, code: str = "BUSINESS_ERROR") -> None:
        self.message = message
        self.code = code

class NotFoundError(BusinessError):
    def __init__(self, resource: str, resource_id: int | str) -> None:
        super().__init__(f"{resource} {resource_id} 不存在", code="NOT_FOUND")

class PermissionDeniedError(BusinessError):
    def __init__(self, message: str = "权限不足") -> None:
        super().__init__(message, code="PERMISSION_DENIED")

class ConflictError(BusinessError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="CONFLICT")
```

### 8.5.2 全局异常处理器

在 `main.py` 中注册异常处理器，将业务异常映射为 HTTP 响应：

```python
def _business_error_to_response(request: Request, exc: BusinessError) -> JSONResponse:
    status_map = {
        NotFoundError: 404,
        PermissionDeniedError: 403,
        ConflictError: 409,
    }
    status_code = status_map.get(type(exc), 400)
    return JSONResponse(
        status_code=status_code,
        content={"code": exc.code, "message": exc.message},
    )

app.add_exception_handler(NotFoundError, _business_error_to_response)
app.add_exception_handler(PermissionDeniedError, _business_error_to_response)
app.add_exception_handler(ConflictError, _business_error_to_response)
```

**统一响应格式**：

```json
// 错误
{"code": "NOT_FOUND", "message": "文章 99999 不存在"}

// 成功（FastAPI 默认）
{"id": 1, "title": "...", "content": "..."}
```

### 8.5.3 结构化日志

用 structlog 输出结构化日志，生产用 JSON，开发用彩色控制台：

```python
# app/core/logging.py
import structlog

def setup_logging(level: str = "INFO", json_output: bool = False) -> None:
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.format_exc_info,
    ]
    if json_output:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())
    structlog.configure(processors=processors, ...)
```

### 8.5.4 trace_id 贯穿

中间件为每个请求注入 `trace_id`，日志自动携带：

```python
# app/main.py
class TraceIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        trace_id = request.headers.get("X-Trace-Id", str(uuid.uuid4()))
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(trace_id=trace_id)
        response = await call_next(request)
        response.headers["X-Trace-Id"] = trace_id
        return response
```

效果：一条请求链路的所有日志都带同一个 `trace_id`，排查问题时按 `trace_id` 过滤即可看到完整链路。

---

## 8.6 API 版本管理

### 8.6.1 URL 前缀法

最实用的版本管理方式：在 URL 中嵌入版本号。

```python
# app/main.py
app.include_router(api_router, prefix=settings.api_v1_prefix)  # /api/v1
```

**优点**：

- 客户端零成本：改 URL 即可
- 缓存友好：不同版本 URL 不同，CDN 可独立缓存
- 文档清晰：Swagger UI 按版本分组

### 8.6.2 多版本共存

当 v2 上线但 v1 仍需维护时：

```
app/api/
├── v1/
│   ├── router.py
│   └── endpoints/
└── v2/
    ├── router.py
    └── endpoints/
```

```python
app.include_router(v1_router, prefix="/api/v1")
app.include_router(v2_router, prefix="/api/v2")
```

### 8.6.3 其他方案对比

| 方案 | 示例 | 优点 | 缺点 |
|---|---|---|---|
| URL 前缀 | `/api/v1/users` | 简单直观、缓存友好 | URL 变长 |
| Header | `Api-Version: 1` | URL 不变 | 不直观、调试难 |
| Accept | `Accept: application/vnd.api.v1+json` | RESTful 纯粹 | 复杂、工具支持差 |

**实践建议**：用 URL 前缀法，简单可靠。

---

## 8.7 测试策略

### 8.7.1 测试分层

```
单元测试（service 层，mock repository）
    ↓
集成测试（endpoint 层，真实数据库 + HTTP 客户端）
    ↓
端到端测试（真实服务 + 真实数据库）
```

本项目以集成测试为主，用 `httpx.AsyncClient` 直传 ASGI，不起真实 HTTP 服务。

### 8.7.2 测试夹具

```python
# tests/conftest.py
import httpx
from httpx import ASGITransport
from sqlalchemy.pool import StaticPool

# 内存 SQLite，StaticPool 确保共享同一数据库
test_engine = create_async_engine(
    "sqlite+aiosqlite://",
    poolclass=StaticPool,
    connect_args={"check_same_thread": False},
)

@pytest_asyncio.fixture
async def client() -> AsyncGenerator[httpx.AsyncClient, None]:
    async def override_get_session():
        async with test_session_factory() as s:
            yield s

    app.dependency_overrides[get_session] = override_get_session
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
```

**关键设计**：

1. **内存 SQLite**：测试不依赖外部数据库，秒级启动
2. **StaticPool**：所有连接共享同一内存数据库
3. **依赖覆盖**：`dependency_overrides[get_session]` 注入测试会话
4. **ASGITransport**：直传 ASGI app，不起真实 HTTP 服务

### 8.7.3 认证辅助夹具

```python
async def register_and_login(client, email="test@example.com", password="testpass123"):
    await client.post("/api/v1/auth/register", json={"email": email, "password": password})
    resp = await client.post("/api/v1/auth/login", data={"username": email, "password": password})
    return resp.json()["access_token"]

@pytest_asyncio.fixture
async def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}
```

### 8.7.4 测试用例示例

```python
class TestCreateArticle:
    async def test_create_success(self, client, auth_headers):
        resp = await client.post(
            "/api/v1/articles/",
            json={"title": "Hello", "content": "World", "tag_ids": []},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["title"] == "Hello"

    async def test_create_without_token(self, client):
        resp = await client.post("/api/v1/articles/", json={"title": "X", "content": "Y"})
        assert resp.status_code == 401

class TestUpdateArticle:
    async def test_update_by_non_author(self, client, auth_headers):
        # 作者创建文章
        create = await client.post(..., headers=auth_headers)
        # 另一个用户尝试修改
        token2 = await register_and_login(client, "other@example.com", "otherpass123")
        resp = await client.put(..., headers={"Authorization": f"Bearer {token2}"})
        assert resp.status_code == 403
```

### 8.7.5 测试覆盖范围

本项目 30 个测试覆盖：

| 模块 | 测试数 | 覆盖场景 |
|---|---|---|
| auth | 8 | 注册成功/重复/短密码/非法邮箱、登录成功/错误密码/不存在、无 token 访问 |
| users | 4 | 获取当前用户、无 token、按 ID 查询、不存在 |
| articles | 17 | CRUD 全流程、分页、权限校验（非作者改/删）、不存在、验证错误 |
| health | 1 | 健康检查 |

---

## 8.8 性能优化

### 8.8.1 连接池调优

```python
engine = create_async_engine(
    settings.database_url,
    pool_size=settings.db_pool_size,      # 常驻连接数
    max_overflow=settings.db_max_overflow,  # 突发时额外连接数
)
```

**调优建议**：

- `pool_size`：根据并发请求数设置，通常 10-20
- `max_overflow`：允许突发超出的连接数，通常 = pool_size
- `pool_timeout`：获取连接超时时间，默认 30s
- `pool_recycle`：连接回收周期，避免数据库端超时（如 3600s）

### 8.8.2 N+1 查询问题

列表查询时，每条记录触发一次关联查询（N+1）。解决方案：

```python
# 模型定义时用 lazy="selectin"
tags: Mapped[list["Tag"]] = relationship(
    secondary=article_tag, lazy="selectin"
)
```

`selectin` 策略：一次 `SELECT ... WHERE id IN (...)` 加载所有关联，2 次查询搞定 N 条记录。

### 8.8.3 响应缓存

高频读取的接口可加缓存：

```python
from fastapi_cache import Cacher
from fastapi_cache.backends.redis import RedisBackend

@app.get("/articles/{id}")
@Cacher(key_builder=lambda r: f"article:{r.path_params['id']}", expire=60)
async def read_article(...):
    ...
```

### 8.8.4 进程管理

生产部署用 gunicorn + uvicorn workers：

```bash
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

- `-w 4`：4 个工作进程（通常 = CPU 核数 × 2 + 1）
- `-k UvicornWorker`：用 uvicorn 的 ASGI worker

### 8.8.5 其他优化方向

| 方向 | 工具 | 说明 |
|---|---|---|
| 查询优化 | SQLAlchemy `explain` | 分析慢查询 |
| 响应压缩 | `GZipMiddleware` | 减少传输体积 |
| 数据库索引 | `index=True` | 加速 WHERE/ORDER BY |
| 分页 | `offset/limit` | 避免一次查太多 |
| 异步任务 | `Celery` / `arq` | 耗时操作不阻塞请求 |

---

## 实践任务与产出

### 任务：完整博客 API

本项目实现了一个完整的博客 API：

**认证流程**：
1. `POST /api/v1/auth/register` — 注册新用户
2. `POST /api/v1/auth/login` — 登录获取 JWT
3. `GET /api/v1/users/me` — 获取当前用户信息

**文章 CRUD**：
1. `POST /api/v1/articles/` — 创建文章（需登录）
2. `GET /api/v1/articles/` — 分页列表
3. `GET /api/v1/articles/{id}` — 文章详情
4. `PUT /api/v1/articles/{id}` — 更新（仅作者）
5. `DELETE /api/v1/articles/{id}` — 删除（仅作者）

**运行方式**：

```bash
cd business-app
uv run uvicorn app.main:app --reload
# 访问 http://localhost:8000/api/v1/docs
```

**测试**：

```bash
uv run pytest tests/ -v
# 30 passed
```

### 产出

- `business-app/` 完整可部署项目（分层架构 + 30 测试）
- 本章文档 ≥ 700 行，覆盖 8 个工程化主题

---

## 小结与下一章衔接

本章从零构建了一个规范化的博客 API，覆盖了真实业务项目需要的所有核心组件：

1. **分层架构**：api → service → repository → model，关注点分离
2. **配置管理**：pydantic-settings，多环境支持
3. **数据库集成**：SQLAlchemy 2.0 async + 仓储模式
4. **认证权限**：OAuth2 + JWT + bcrypt + 权限校验
5. **错误处理**：业务异常体系 + 全局处理器 + 统一响应
6. **结构化日志**：structlog + trace_id 贯穿
7. **API 版本**：URL 前缀法
8. **测试策略**：httpx + 内存 SQLite + 30 测试覆盖

下一章将把整个学习项目沉淀为文档站并部署上线。

---

!!! tip "与造轮子的对照"
    在阶段 1-7 中，我们手写了 FastAPI 的核心机制。本章用官方 FastAPI 时，你已经知道：

    - `Depends` 背后是 `solve_dependencies` 递归解析（阶段 4）
    - `APIRouter` 背后是 `Route` 匹配 + `include_router` 合并（阶段 3）
    - `OAuth2PasswordBearer` 背后是 ASGI scope 中的 header 提取（阶段 5）
    - 异常处理器背后是 `exception_handlers` 字典查找（阶段 6）
    - 中间件背后是 ASGI `__call__` 链式调用（阶段 6）

    这种"上帝视角"让你写出的代码更有信心——你知道每个装饰器、每个依赖在框架内部经历了什么。
