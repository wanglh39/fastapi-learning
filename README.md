# FastAPI 系统化学习与实践项目

从底层原理到业务实践，系统掌握 FastAPI 框架。本项目通过**亲手造一个类 FastAPI 轻量级框架**来深入理解其内部机制，并用**官方 FastAPI** 完成一个规范化业务项目，最终沉淀为文档站。

> 文档站地址（GitHub Pages 启用后）：见 `docs/` 目录配置说明。

---

## 项目结构

```
fastapi-learning/
├── docs/                  # MkDocs Material 文档源（学习笔记 → 文档站）
├── mini-fastapi/          # 造轮子项目：从零实现类 FastAPI 框架（核心产出）
├── business-app/          # 业务实践项目：用官方 FastAPI 实现博客 API
├── notes/                 # 学习笔记草稿（最终整理进 docs/）
└── README.md
```

### 两个子项目的关系

| 项目 | 作用 | 技术栈 |
|------|------|--------|
| `mini-fastapi` | 造轮子，理解 FastAPI 内部机制 | 纯 Python + Pydantic + uvicorn |
| `business-app` | 真实业务工程化最佳实践 | FastAPI + SQLAlchemy 2.0 async + JWT |

先造轮子理解原理，再用真框架做业务，此时对框架行为有"上帝视角"。

---

## 学习路径（10 个阶段）

| 阶段 | 主题 | 产出 |
|------|------|------|
| 0 | 环境与基础准备 | 项目骨架 + 文档站 |
| 1 | ASGI 协议与 Starlette | mini-fastapi v0.0 |
| 2 | Pydantic 与类型系统 | 参数验证脚本 |
| 3 | 路由与参数绑定 | mini-fastapi v0.1–v0.3 |
| 4 | 依赖注入系统 | mini-fastapi v0.4 |
| 5 | 自动文档生成 | mini-fastapi v0.5 |
| 6 | 中间件、异常、异步 | mini-fastapi v0.6 |
| 7 | 框架对比与选型 | 对比分析长文 |
| 8 | 业务工程化实践 | business-app 完整项目 |
| 9 | 沉淀与发布 | 文档站成书 |

详细路径见文档站「学习路径总览」章节。

---

## 环境要求

- Python ≥ 3.11
- [uv](https://github.com/astral-sh/uv) 作为环境与包管理器
- Node.js（仅 MkDocs Material 主题构建可选）

---

## 快速开始

### 造轮子项目

```bash
cd mini-fastapi
uv sync
uv run uvicorn examples.hello:app --reload
```

### 业务项目

```bash
cd business-app
uv sync
uv run uvicorn app.main:app --reload
```

### 文档站本地预览

```bash
cd docs
uv run --with-requirements requirements-docs.txt mkdocs serve
```

访问 http://127.0.0.1:8000

---

## 造轮子里程碑

| 版本 | 能力 |
|------|------|
| v0.0 | 纯 ASGI app |
| v0.1 | 路由装饰器 + 路径参数 |
| v0.2 | 查询参数 + 请求体（Pydantic） |
| v0.3 | 响应模型 + 状态码 |
| v0.4 | 依赖注入 Depends |
| v0.5 | OpenAPI 自动文档 + Swagger UI |
| v0.6 | 中间件 + 异常处理 |
| v0.7 | 异步 DB 集成示例 |
| v1.0 | 完整示例 + 测试 + 文档 |

---

## 许可

仅用于学习目的。