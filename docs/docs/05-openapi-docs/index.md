# 阶段 5 · 自动文档生成

!!! info "本章定位"
    FastAPI"类型优先"哲学的集中兑现：类型注解 → Pydantic schema → OpenAPI JSON → Swagger UI / ReDoc。本章实现 mini-fastapi v0.5。

---

## 本章学习目标

读完本章后，你应当能够：

1. 理解 OpenAPI 3.1 规范的核心结构
2. 从路由签名 + Pydantic 模型生成 OpenAPI JSON
3. 挂载 `/openapi.json`、`/docs`（Swagger UI）、`/redoc`
4. 解释"类型优先"如何消灭样板代码
5. 对比你生成的 schema 与真 FastAPI 的差异

---

## 小节目录

1. [OpenAPI 3.1 规范结构](#51-openapi-31-规范结构)
2. [从路由到 operation](#52-从路由到-operation)
3. [从 Pydantic 模型到 schema](#53-从-pydantic-模型到-schema)
4. [汇总生成 OpenAPI 文档](#54-汇总生成-openapi-文档)
5. [挂载 Swagger UI 与 ReDoc](#55-挂载-swagger-ui-与-redoc)
6. [在 mini-fastapi 中实现](#56-在-mini-fastapi-中实现)
7. [与 FastAPI 源码对照](#57-与-fastapi-源码对照)
8. [实践任务与产出](#58-实践任务与产出)
9. [小结与下一章衔接](#59-小结与下一章衔接)

---

## 5.1 OpenAPI 3.1 规范结构

待补充：讲 OpenAPI 文档顶层结构（`openapi`、`info`、`paths`、`components`、`servers`），重点展开 `paths` 的 operation 结构（`parameters`、`requestBody`、`responses`）与 `components.schemas` 的复用机制。

---

## 5.2 从路由到 operation

待补充：遍历每条注册路由，生成一个 operation 对象，包含：

- `parameters`：路径参数与查询参数（in: path/query）
- `requestBody`：若端点有 BaseModel 参数，引用对应 schema
- `responses`：按 `response_model` 与 `status_code` 生成

---

## 5.3 从 Pydantic 模型到 schema

待补充：调用 `Model.model_json_schema()` 拿到模型 schema，放入 `components.schemas`，operation 中用 `$ref` 引用以实现复用。

---

## 5.4 汇总生成 OpenAPI 文档

待补充：给出 `get_openapi(title, version, routes)` 的完整实现，遍历路由汇总 paths 与 schemas。

---

## 5.5 挂载 Swagger UI 与 ReDoc

待补充：`/docs` 返回内嵌 Swagger UI 的 HTML（引用 CDN 的 swagger-ui-bundle），`/openapi.json` 返回生成的 JSON。ReDoc 同理。

---

## 5.6 在 mini-fastapi 中实现

### 5.6.1 get_openapi 实现

待补充：完整代码与逐行解读。

### 5.6.2 setup_docs 挂载

待补充：在 MiniFastAPI 中挂载三个文档路由。

### 5.6.3 跑通验证

待补充：启动 mini-fastapi，访问 `/docs` 看到 Swagger UI，能在线测试接口。

---

## 5.7 与 FastAPI 源码对照

待补充：对照 `fastapi/openapi.py` 的 `get_openapi`，找出差异（如 tags、security、deprecated 支持），分析简化是否影响核心。

---

## 5.8 实践任务与产出

### 任务：文档驱动开发

先写接口签名与模型，启动后从 `/docs` 验证契约正确，再实现业务逻辑——体验"文档先行"。

### 产出

- mini-fastapi v0.5（打 git tag）
- 本章笔记（≥ 700 行）

---

## 5.9 小结与下一章衔接

本章让 mini-fastapi 有了"招牌"。下一章补齐"神经"——中间件、异常处理与异步深入。

---

!!! todo "待填充标记说明"
    本文件为大纲骨架，标注「待补充」处为后续要展开的内容点。每个待补充点都已规划好要讲的核心问题与示例方向，填充时直接展开即可达到 ≥ 700 行深度。**笔记深度与数量只增不减**，本骨架的小节结构在填充时只会扩充不会删减。