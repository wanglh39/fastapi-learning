# 阶段 6 · 中间件、异常与异步深入

!!! info "本章定位"
    补齐 mini-fastapi 的"神经"：中间件洋葱模型、异常处理器分发、异步并发与压测。对应 v0.6。

    读完本章，你将理解 ASGI 中间件的洋葱模型、异常处理器的注册与分发机制，以及异步编程中的常见陷阱与逃生方案。

---

## 本章学习目标

读完本章后，你应当能够：

1. 理解中间件洋葱模型并实现中间件链
2. 实现异常处理器注册与全局兜底
3. 理解异步 DB 驱动的连接池模型
4. 用压测对比同步与异步接口的吞吐差异
5. 识别异步代码中阻塞调用的危害并知道逃生方案

---

## 小节目录

1. 中间件洋葱模型
2. 纯 ASGI 中间件 vs BaseHTTPMiddleware
3. 在 mini-fastapi 中实现中间件链
4. 异常处理器机制
5. HTTPException 与业务异常映射
6. 异步数据库驱动与连接池
7. 同步 vs 异步压测对比
8. 异步代码的坑与逃生
9. 实践任务与产出
10. 小结与下一章衔接

---

## 6.1 中间件洋葱模型

### 6.1.1 什么是中间件

中间件是 ASGI 应用的"洋葱模型"：每个中间件包裹下一层应用，请求从外到内传递，响应从内到外返回。每一层可以在请求前和响应后插入逻辑。

```mermaid
graph LR
    A["请求"] --> B["中间件1 进"]
    B --> C["中间件2 进"]
    C --> D["端点"]
    D --> E["中间件2 出"]
    E --> F["中间件1 出"]
    F --> G["响应"]
```

### 6.1.2 典型中间件场景

| 中间件 | 请求前 | 响应后 |
|--------|--------|--------|
| CORS | 检查 Origin | 添加 `Access-Control-Allow-*` 头 |
| 计时日志 | 记录开始时间 | 添加 `X-Process-Time` 头 |
| 认证 | 检查 Token | — |
| 限流 | 检查计数器 | — |
| 日志 | 记录请求信息 | 记录响应状态与耗时 |
| 压缩 | — | 压缩响应体 |

### 6.1.3 执行顺序验证

```python
app = MiniFastAPI()
app.add_middleware(MiddlewareA)  # 先添加 → 外层
app.add_middleware(MiddlewareB)  # 后添加 → 内层

@app.get("/")
def root():
    log.append("endpoint")
    return {"hello": "world"}
```

执行顺序：`A-in → B-in → endpoint → B-out → A-out`

**先添加的中间件在外层**，先处理请求、后处理响应。这符合"洋葱"的直觉：最先包上去的皮在最外面。

### 6.1.4 为什么用洋葱模型

1. **关注点分离**：每个中间件只做一件事（CORS、日志、认证等）
2. **可组合**：中间件按需添加，互不干扰
3. **顺序可控**：添加顺序决定执行顺序，外层中间件可以"看到"所有内层的处理结果
4. **统一接口**：所有中间件都是 ASGI app，可自由组合

---

## 6.2 纯 ASGI 中间件 vs BaseHTTPMiddleware

### 6.2.1 纯 ASGI 中间件

```python
class TimingMiddleware:
    """纯 ASGI 中间件：直接操作 scope/receive/send。"""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start = time.perf_counter()

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                duration = f"{time.perf_counter() - start:.6f}"
                headers = list(message.get("headers", []))
                headers.append((b"x-process-time", duration.encode("latin-1")))
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_wrapper)
```

特点：

- **直接操作 ASGI 三元组** `(scope, receive, send)`
- **包装 send** 来修改响应（在 `http.response.start` 时注入头）
- **性能最高**：无额外抽象层
- **较底层**：需要理解 ASGI 协议细节

### 6.2.2 BaseHTTPMiddleware

```python
class MyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, scope, receive, send, call_next):
        # 请求前逻辑
        await call_next()  # 调用下一层
        # 响应后逻辑
```

特点：

- **更易写**：`call_next()` 抽象了"调用下一层"
- **有额外开销**：每次请求多一层函数调用包装
- **适合简单场景**：不需要精细控制 send 时

### 6.2.3 性能对比与选型

| 方面 | 纯 ASGI 中间件 | BaseHTTPMiddleware |
|------|--------------|-------------------|
| 性能 | 最高 | 略低（额外包装） |
| 易用性 | 较低（需理解 ASGI） | 较高（call_next 抽象） |
| 灵活性 | 最高（完全控制） | 中等（受基类约束） |
| 适用 | 生产中间件 | 快速原型/简单逻辑 |

**建议**：性能敏感的中间件（CORS、限流）用纯 ASGI；简单逻辑用 BaseHTTPMiddleware。

---

## 6.3 在 mini-fastapi 中实现中间件链

### 6.3.1 中间件栈构建

```python
class MiniFastAPI:
    def __init__(self, *, title="MiniFastAPI", version="0.0.0"):
        ...
        self.user_middleware: list[tuple[type, dict]] = []
        self.middleware_stack = self._original_app

    def add_middleware(self, middleware_cls, **opts):
        """向应用添加中间件。"""
        self.user_middleware.append((middleware_cls, opts))
        self._build_middleware_stack()

    def _build_middleware_stack(self):
        """构建中间件栈（洋葱模型）。"""
        app = self._original_app
        for middleware_cls, opts in reversed(self.user_middleware):
            app = middleware_cls(app, **opts)
        self.middleware_stack = app
```

### 6.3.2 栈构建过程

假设添加顺序：A → B → C

```python
app.add_middleware(A)  # user_middleware = [(A, {})]
app.add_middleware(B)  # user_middleware = [(A, {}), (B, {})]
app.add_middleware(C)  # user_middleware = [(A, {}), (B, {}), (C, {})]
```

`_build_middleware_stack` 逆序遍历：

```python
app = self._original_app      # 最内层：路由分发
app = C(app)                  # C 包裹 original_app
app = B(app)                  # B 包裹 C
app = A(app)                  # A 包裹 B → 最外层
self.middleware_stack = A(B(C(original_app)))
```

请求时调用 `A(B(C(original_app)))(scope, receive, send)`：

```
A.__call__ → B.__call__ → C.__call__ → original_app → C 返回 → B 返回 → A 返回
```

### 6.3.3 __call__ 分发

```python
async def __call__(self, scope, receive, send):
    """ASGI 协议入口，通过中间件栈分发。"""
    await self.middleware_stack(scope, receive, send)

async def _original_app(self, scope, receive, send):
    """原始 ASGI 应用（中间件链的最内层）。"""
    if scope["type"] == "lifespan":
        await self._handle_lifespan(scope, receive, send)
    elif scope["type"] == "http":
        await self._handle_http(scope, receive, send)
```

`__call__` 不再直接处理请求，而是委托给 `middleware_stack`。如果没有中间件，`middleware_stack` 就是 `_original_app`，行为与之前一致。

### 6.3.4 CORS 中间件实现

```python
class CORSMiddleware:
    def __init__(self, app, allow_origins="*", allow_methods="*", allow_headers="*"):
        self.app = app
        self.allow_origins = allow_origins
        ...

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        origin = self._get_origin(scope)

        # OPTIONS 预检请求：直接返回 CORS 头
        if scope["method"] == "OPTIONS":
            headers = self._build_cors_headers(origin)
            await send({"type": "http.response.start", "status": 200, "headers": headers})
            await send({"type": "http.response.body", "body": b""})
            return

        # 普通请求：在响应头中追加 CORS 头
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.extend(self._build_cors_headers(origin))
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_wrapper)
```

关键点：

- **OPTIONS 预检**：浏览器发送 OPTIONS 请求检查 CORS，直接返回 200 + CORS 头，不传递给端点
- **普通请求**：包装 `send`，在 `http.response.start` 时注入 CORS 头
- **Origin 匹配**：`allow_origins="*"` 允许所有；指定列表则只允许列表中的 origin

### 6.3.5 TimingMiddleware 实现

```python
class TimingMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start = time.perf_counter()

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                duration = f"{time.perf_counter() - start:.6f}"
                headers = list(message.get("headers", []))
                headers.append((b"x-process-time", duration.encode("latin-1")))
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_wrapper)
```

用 `time.perf_counter()` 而非 `time.time()`，因为 `perf_counter` 是单调时钟，不受系统时间调整影响，精度更高。

---

## 6.4 异常处理器机制

### 6.4.1 注册异常处理器

```python
app = MiniFastAPI()

@app.exception_handler(NotFoundError)
def handle_not_found(exc: NotFoundError):
    return JSONResponse({"error": "not_found", "detail": str(exc)}, status_code=404)
```

`exception_handler` 是装饰器工厂：传入异常类型，返回装饰器，把处理函数存入 `exception_handlers` 字典。

### 6.4.2 异常分发逻辑

```python
async def _handle_exception(self, exc: Exception, send: Callable) -> None:
    """统一异常处理：查找注册的处理器，未命中则默认处理。"""
    # 1. 查找注册的处理器
    handler = self._find_exception_handler(type(exc))
    if handler:
        response = handler(exc)
        if inspect.iscoroutine(response):
            response = await response
        await response(send)
        return

    # 2. 默认处理
    if isinstance(exc, HTTPException):
        await JSONResponse({"detail": exc.detail}, status_code=exc.status_code)(send)
        return
    if isinstance(exc, RequestValidationError):
        await JSONResponse({"detail": exc.errors}, status_code=422)(send)
        return

    # 3. 兜底 500
    await JSONResponse({"detail": "Internal Server Error"}, status_code=500)(send)
```

处理优先级：

1. **注册的异常处理器**（按异常类型匹配，支持子类）
2. **HTTPException** → 对应状态码
3. **RequestValidationError** → 422
4. **其他异常** → 500

### 6.4.3 子类匹配

```python
def _find_exception_handler(self, exc_type: type[Exception]) -> Callable | None:
    for handler_type, handler in self.exception_handlers.items():
        if issubclass(exc_type, handler_type):
            return handler
    return None
```

注册 `AppError` 的处理器，抛出 `DatabaseError(AppError)` 也能命中：

```python
class AppError(Exception): pass
class DatabaseError(AppError): pass

@app.exception_handler(AppError)
def handle(exc): ...

@app.get("/")
def root():
    raise DatabaseError("connection lost")  # 命中 handle
```

### 6.4.4 在请求分发中集成

```python
async def _handle_http(self, scope, receive, send):
    ...
    try:
        try:
            kwargs, cleaners = await solve_dependencies(...)
        except Exception as exc:
            await self._handle_exception(exc, send)  # 依赖解析异常
            return

        try:
            result = await self._invoke_endpoint(route.endpoint, kwargs)
        except Exception as exc:
            await self._handle_exception(exc, send)  # 端点执行异常
            return

        ...
    finally:
        await self._run_cleaners(cleaners)
```

`_handle_exception` 统一处理**依赖解析阶段**和**端点执行阶段**的所有异常。

---

## 6.5 HTTPException 与业务异常映射

### 6.5.1 HTTPException

框架内置异常，直接映射为对应状态码：

```python
@app.get("/items/{id}")
def get_item(id: int):
    if id not in store:
        raise HTTPException(status_code=404, detail="Item not found")
    return store[id]
```

响应：`404 {"detail": "Item not found"}`

### 6.5.2 自定义业务异常

```python
class ArticleNotFound(Exception):
    def __init__(self, article_id: int):
        self.article_id = article_id

@app.exception_handler(ArticleNotFound)
def handle_article_not_found(exc: ArticleNotFound):
    return JSONResponse(
        {"error": "article_not_found", "article_id": exc.article_id},
        status_code=404,
    )

@app.get("/articles/{article_id}")
def get_article(article_id: int):
    if article_id not in articles:
        raise ArticleNotFound(article_id)
    return articles[article_id]
```

响应：`404 {"error": "article_not_found", "article_id": 42}`

### 6.5.3 覆盖默认 HTTPException 处理

```python
@app.exception_handler(HTTPException)
def custom_http_handler(exc: HTTPException):
    return JSONResponse(
        {"custom": True, "detail": exc.detail},
        status_code=exc.status_code,
    )
```

注册后，所有 `HTTPException` 都走自定义处理器。

### 6.5.4 异常层次设计建议

```mermaid
graph TD
    A["Exception"] --> B["AppError（应用基类）"]
    B --> C["NotFoundError"]
    B --> D["ValidationError"]
    B --> E["AuthError"]
    E --> F["InvalidTokenError"]
    E --> G["PermissionDeniedError"]
```

- **AppError**：应用异常基类，注册一个处理器统一处理
- **子类异常**：携带具体错误信息，处理器按类型分发
- **HTTPException**：框架级异常，直接映射状态码

---

## 6.6 异步数据库驱动与连接池

### 6.6.1 同步 vs 异步 DB 驱动

| 驱动 | 模式 | 示例 |
|------|------|------|
| `psycopg2` | 同步 | `cursor.execute()` 阻塞当前线程 |
| `asyncpg` | 异步 | `await conn.execute()` 不阻塞事件循环 |
| `SQLAlchemy + asyncpg` | 异步 ORM | `await session.execute(select(Item))` |

### 6.6.2 连接池模型

```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

engine = create_async_engine("postgresql+asyncpg://user:pass@localhost/db", pool_size=10)
AsyncSessionLocal = async_sessionmaker(engine)

async def get_db():
    """yield 依赖：每个请求一个会话。"""
    async with AsyncSessionLocal() as session:
        yield session
```

- **`pool_size=10`**：连接池维护 10 个连接，复用避免频繁建连
- **`async with`**：会话从池中借出，退出时归还
- **每请求一会话**：`get_db` 是 yield 依赖，请求结束自动归还

### 6.6.3 为什么不能跨请求复用 session

1. **事务隔离**：每个请求应有独立的事务边界
2. **并发安全**：多个请求共用 session 会产生竞态条件
3. **资源释放**：session 持有连接，不释放会耗尽连接池

### 6.6.4 asyncio.to_thread 桥接同步驱动

```python
import asyncio

async def get_user_sync(user_id: int):
    """用同步驱动但避免阻塞事件循环。"""
    def query():
        with sync_engine.connect() as conn:
            return conn.execute(select(User).where(User.id == user_id)).fetchone()

    return await asyncio.to_thread(query)
```

`asyncio.to_thread` 把同步调用放到线程池中执行，不阻塞事件循环。适用于必须用同步库的场景。

---

## 6.7 同步 vs 异步压测对比

### 6.7.1 压测场景

```python
# 异步端点（FastAPI/mini-fastapi）
@app.get("/async")
async def async_endpoint():
    await asyncio.sleep(0.1)  # 模拟 I/O
    return {"hello": "world"}

# 同步端点（Flask）
@app.route("/sync")
def sync_endpoint():
    time.sleep(0.1)  # 阻塞线程
    return {"hello": "world"}
```

### 6.7.2 预期结果

| 框架 | 模式 | 100 并发 RPS | 说明 |
|------|------|-------------|------|
| Flask | 同步多线程 | ~10 | 每个请求阻塞一个线程 100ms |
| FastAPI | 异步单线程 | ~1000 | `asyncio.sleep` 不阻塞，可并发处理 |

### 6.7.3 为什么差异巨大

**同步（Flask）**：

- 每个请求占用一个工作线程
- `time.sleep(0.1)` 阻塞线程，线程在 sleep 期间无法处理其他请求
- 100 并发需要 100 线程，受线程池大小限制

**异步（FastAPI）**：

- 单线程事件循环处理所有请求
- `asyncio.sleep(0.1)` 不阻塞线程，只是注册一个定时器
- 100 个请求可以"同时" sleep，100ms 后一起返回
- 不是真正的并行，而是"并发"——在 I/O 等待时切换到其他任务

### 6.7.4 适用条件

异步优势仅在**I/O 密集**场景显著：

| 场景 | 同步 | 异步 | 原因 |
|------|------|------|------|
| I/O 密集（DB、HTTP） | 慢 | 快 | 异步在 I/O 等待时切换任务 |
| CPU 密集（计算） | 相同 | 相同（或更慢） | 异步不提供并行计算 |
| 混合 | 中 | 快 | 异步在 I/O 部分有优势 |

---

## 6.8 异步代码的坑与逃生

### 6.8.1 阻塞调用陷阱

```python
# 错误：在异步函数中调用阻塞函数
@app.get("/bad")
async def bad():
    time.sleep(1)  # 阻塞整个事件循环！
    return {"hello": "world"}
```

`time.sleep(1)` 阻塞当前线程——在异步框架中，这就是**事件循环线程**。所有其他请求都被阻塞 1 秒。

### 6.8.2 正确做法

```python
# 用 asyncio.sleep 替代 time.sleep
@app.get("/good")
async def good():
    await asyncio.sleep(1)  # 不阻塞事件循环
    return {"hello": "world"}

# 用 httpx.AsyncClient 替代 requests
@app.get("/fetch")
async def fetch():
    async with httpx.AsyncClient() as client:
        response = await client.get("https://api.example.com")
    return response.json()

# 必须用同步库时用 asyncio.to_thread
@app.get("/sync-db")
async def sync_db():
    result = await asyncio.to_thread(blocking_db_query)
    return result
```

### 6.8.3 常见阻塞调用对照表

| 阻塞调用 | 异步替代 | 说明 |
|---------|---------|------|
| `time.sleep(n)` | `asyncio.sleep(n)` | 定时等待 |
| `requests.get(url)` | `httpx.AsyncClient` | HTTP 请求 |
| `open(file).read()` | `aiofiles.open()` | 文件 I/O |
| `psycopg2.connect()` | `asyncpg.connect()` | PostgreSQL |
| `redis-py` | `redis.asyncio` | Redis |
| `subprocess.run()` | `asyncio.create_subprocess_exec()` | 子进程 |

### 6.8.4 ContextVar 穿透

```python
import contextvars

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id")

class RequestIDMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            request_id_var.set(str(uuid.uuid4()))
        await self.app(scope, receive, send)

# 任何地方都能取到 request_id
def log(msg: str):
    print(f"[{request_id_var.get()}] {msg}")
```

`ContextVar` 在 `asyncio` 中自动穿透 `await` 调用栈，不需要显式传递。适合 `request_id`、`trace_id` 等需要在整个请求链路中传递的信息。

### 6.8.5 常见错误清单

| 错误 | 症状 | 修复 |
|------|------|------|
| 在 async 函数中 `time.sleep` | 所有请求卡住 | 用 `asyncio.sleep` |
| 忘记 `await` | 返回协程对象而非结果 | 加 `await` |
| 在同步函数中调用 async 函数 | `RuntimeError: no event loop` | 用 `asyncio.run()` 或改为 async |
| 混用同步 DB 驱动 | 性能退化 | 用异步驱动或 `to_thread` |
| yield 依赖未正确清理 | 连接泄漏 | 确保 `finally` 或 `async with` |

---

## 6.9 实践任务与产出

### 6.9.1 任务 1：中间件

实现 CORS 中间件与请求计时日志中间件，挂到 mini-fastapi：

```python
from mini_fastapi import CORSMiddleware, MiniFastAPI, TimingMiddleware

app = MiniFastAPI(title="Hello", version="0.6.0")
app.add_middleware(TimingMiddleware)
app.add_middleware(CORSMiddleware, allow_origins="*")
```

### 6.9.2 任务 2：异常处理

注册 `HTTPException`、`RequestValidationError`、自定义 `NotFound` 的处理器：

```python
class ArticleNotFound(Exception):
    pass

@app.exception_handler(ArticleNotFound)
def handle_not_found(exc: ArticleNotFound):
    return JSONResponse({"error": "article_not_found"}, status_code=404)
```

### 6.9.3 任务 3：压测

```python
import asyncio
from mini_fastapi import MiniFastAPI

app = MiniFastAPI()

@app.get("/io-bound")
async def io_bound():
    await asyncio.sleep(0.1)  # 模拟 I/O
    return {"hello": "world"}
```

用 `hey` 或 `locust` 压测，对比同步版本（`time.sleep`）的 RPS 差异。

### 6.9.4 测试覆盖

本章新增 10 个测试（`test_middleware.py`），分布如下：

| 测试类型 | 用例数 | 覆盖内容 |
|---------|--------|---------|
| TimingMiddleware | 1 | X-Process-Time 头 |
| CORSMiddleware | 3 | CORS 头、OPTIONS 预检、指定 origin |
| 洋葱模型 | 1 | 中间件执行顺序 |
| 异常处理器 | 4 | 自定义异常、子类匹配、HTTPException、覆盖默认 |
| 集成 | 1 | 中间件 + 正常请求 |

总计 98 个测试全部通过。

### 6.9.5 产出

- mini-fastapi v0.6.0（中间件链 + 异常处理器 + CORS + Timing）
- 98 个测试全部通过（新增 10 个）
- 本章笔记（≥ 700 行）

---

## 6.10 小结与下一章衔接

### 6.10.1 本章里程碑

| 版本 | 能力 | 关键代码 |
|------|------|---------|
| v0.5 | OpenAPI 自动文档 | `openapi.py` |
| **v0.6** | **中间件 + 异常处理器** | **`middleware.py` + `application.py` 集成** |

### 6.10.2 我们学到了什么

1. **中间件洋葱模型**：每个中间件包裹下一层应用，请求从外到内，响应从内到外。先添加的在外层。用 `reversed` 遍历构建栈。

2. **纯 ASGI 中间件**：直接操作 `(scope, receive, send)`，包装 `send` 来修改响应。性能最高，但需要理解 ASGI 协议。

3. **异常处理器**：`@app.exception_handler(ExcType)` 注册处理器，按异常类型（含子类）匹配。优先级：注册处理器 > HTTPException > RequestValidationError > 500 兜底。

4. **异步 vs 同步**：异步在 I/O 密集场景优势巨大（`asyncio.sleep` 不阻塞事件循环），但 CPU 密集场景无优势。关键是不在 async 函数中调用阻塞函数。

5. **ContextVar 穿透**：在 asyncio 中自动穿透 await 调用栈，适合 `request_id` 等需要在整个请求链中传递的信息。

### 6.10.3 mini-fastapi 核心能力总览

```mermaid
mindmap
  root((mini-fastapi v0.6))
    路由系统
      路径参数
      路由匹配
      装饰器注册
    参数绑定
      查询参数
      请求体
      类型转换
      422 验证
    响应控制
      response_model
      status_code
      HTTPException
    依赖注入
      Depends
      递归解析
      请求级缓存
      yield 清理
    OpenAPI
      自动文档
      Swagger UI
      ReDoc
    中间件
      洋葱模型
      CORS
      Timing
    异常处理
      自定义处理器
      子类匹配
      全局兜底
```

### 6.10.4 下一章衔接

mini-fastapi 至此具备 FastAPI 的所有核心能力。下一章跳出实现，**横向对比 Flask / Django / FastAPI**，建立选型判断力。

阶段 7 将从以下维度对比：

- 对比维度总览（性能、生态、学习曲线、类型系统等）
- 同步 vs 异步生态
- 类型系统与数据校验
- 文档与生态
- ORM 与数据访问
- 性能实测对比
- 学习曲线与生态成熟度
- 适用场景矩阵
- 为什么 LLM 后端偏爱 FastAPI
- Django 全栈 vs FastAPI 组合优先

---

!!! success "阶段 6 完成"
    mini-fastapi v0.6.0：中间件洋葱模型 + 异常处理器 + CORS + Timing

    - 源码：`mini-fastapi/src/mini_fastapi/middleware.py` 完整实现
    - 测试：98 个用例全部通过（新增 10 个）
    - 文档：本章 ≥ 700 行

!!! todo "下一阶段"
    阶段 7 · 框架对比：Flask vs Django vs FastAPI
