# 阶段 6 · 中间件、异常与异步深入

!!! info "本章定位"
    补齐 mini-fastapi 的"神经"：中间件洋葱模型、异常处理器分发、异步并发与压测。对应 v0.6。

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

1. [中间件洋葱模型](#61-中间件洋葱模型)
2. [纯 ASGI 中间件 vs BaseHTTPMiddleware](#62-纯-asgi-中间件-vs-basehttpmiddleware)
3. [在 mini-fastapi 中实现中间件链](#63-在-mini-fastapi-中实现中间件链)
4. [异常处理器机制](#64-异常处理器机制)
5. [HTTPException 与业务异常映射](#65-httpexception-与业务异常映射)
6. [异步数据库驱动与连接池](#66-异步数据库驱动与连接池)
7. [同步 vs 异步压测对比](#67-同步-vs-异步压测对比)
8. [异步代码的坑与逃生](#68-异步代码的坑与逃生)
9. [实践任务与产出](#69-实践任务与产出)
10. [小结与下一章衔接](#610-小结与下一章衔接)

---

## 6.1 中间件洋葱模型

```mermaid
graph LR
    A[请求] --> B[中间件1 进]
    B --> C[中间件2 进]
    C --> D[端点]
    D --> E[中间件2 出]
    E --> F[中间件1 出]
    F --> G[响应]
```

待补充：讲请求从外到内、响应从内到外的执行顺序，用 CORS + 计时日志两个中间件演示。

---

## 6.2 纯 ASGI 中间件 vs BaseHTTPMiddleware

待补充：纯 ASGI 中间件直接操作 `scope/receive/send`，性能最高但较底层；`BaseHTTPMiddleware` 包装成 Request/Response 对象，易写但有额外开销。给出性能对比与选型建议。

---

## 6.3 在 mini-fastapi 中实现中间件链

待补充：给出中间件链组装的完整实现——每个中间件包裹下一层 app，最内层是路由分发。`add_middleware` 如何维护顺序。

---

## 6.4 异常处理器机制

待补充：`@app.exception_handler(SomeException)` 注册处理器，请求分发时 try/except 捕获异常，按异常类型（含子类）查找处理器，未命中则全局兜底 500。

---

## 6.5 HTTPException 与业务异常映射

待补充：`HTTPException` 直接映射为对应状态码响应；自定义业务异常（如 `ArticleNotFound`）通过注册处理器映射为友好 JSON。

---

## 6.6 异步数据库驱动与连接池

待补充：讲 `asyncpg` / SQLAlchemy async 的连接池模型——池大小、`async with session` 的语义、为什么不能跨请求复用 session、`asyncio.to_thread` 处理同步驱动。

---

## 6.7 同步 vs 异步压测对比

待补充：用 `hey` 或 `locust` 压测一个有 DB/HTTP 调用的接口，对比 Flask（同步多线程）与 FastAPI（异步）的 RPS 与延迟分布，给出数据表与解读。

---

## 6.8 异步代码的坑与逃生

待补充：

- 在异步函数里调用 `time.sleep` / `requests.get` 会阻塞整个事件循环
- 用 `asyncio.sleep` / `httpx.AsyncClient` 替代
- 必须用同步库时用 `asyncio.to_thread` 桥接
- 异步上下文中的 `ContextVar` 穿透

---

## 6.9 实践任务与产出

### 任务 1：中间件

实现 CORS 中间件与请求计时日志中间件，挂到 mini-fastapi。

### 任务 2：异常处理

注册 `HTTPException`、`RequestValidationError`、自定义 `NotFound` 的处理器。

### 任务 3：压测

写一个带 `await asyncio.sleep(0.1)` 模拟 I/O 的接口，压测对比同步版本。

### 产出

- mini-fastapi v0.6（打 git tag）
- 压测报告笔记
- 本章笔记（≥ 700 行）

---

## 6.10 小结与下一章衔接

mini-fastapi 至此具备核心能力。下一章跳出实现，横向对比 Flask / Django / FastAPI，建立选型判断力。

---

!!! todo "待填充标记说明"
    本文件为大纲骨架，标注「待补充」处为后续要展开的内容点。每个待补充点都已规划好要讲的核心问题与示例方向，填充时直接展开即可达到 ≥ 700 行深度。**笔记深度与数量只增不减**，本骨架的小节结构在填充时只会扩充不会删减。