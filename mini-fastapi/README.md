# mini-fastapi

从零实现的类 FastAPI 轻量级框架，用于深入理解 FastAPI 内部机制。

## 运行

```bash
uv sync
uv sync --extra test      # 安装测试依赖
uv run pytest             # 运行测试
uv run uvicorn examples.hello:app --reload
```

## 演进里程碑

| 版本 | 能力 | 状态 |
|------|------|------|
| v0.0 | 项目骨架 | ✅ |
| v0.1 | 路由装饰器 + 路径参数 | ⬜ 阶段 1 |
| v0.2 | 查询参数 + 请求体 | ⬜ 阶段 3 |
| v0.3 | 响应模型 + 状态码 | ⬜ 阶段 3 |
| v0.4 | 依赖注入 Depends | ⬜ 阶段 4 |
| v0.5 | OpenAPI 自动文档 | ⬜ 阶段 5 |
| v0.6 | 中间件 + 异常处理 | ⬜ 阶段 6 |
| v0.7 | 异步 DB 集成 | ⬜ 阶段 8 |
| v1.0 | 完整示例 + 测试 | ⬜ 阶段 9 |

每个模块顶部 docstring 标注了对应 FastAPI 源码位置与演进计划。