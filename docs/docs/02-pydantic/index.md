# 阶段 2 · Pydantic 与类型系统

!!! info "本章定位"
    FastAPI"类型优先"哲学的根基。理解了 Pydantic，就理解了 FastAPI 参数验证与自动文档的源头。

---

## 本章学习目标

读完本章后，你应当能够：

1. 理解 Pydantic v2 的核心模型机制：验证、序列化、JSON Schema 生成
2. 说清类型注解如何驱动运行时验证
3. 对比 `dataclass`、`TypedDict`、`BaseModel` 三种数据建模方式的取舍
4. 理解 Pydantic v2 的 Rust 内核 `pydantic-core` 带来的性能提升
5. 解释 FastAPI 为什么选择 Pydantic 而非 marshmallow
6. 用 `inspect.signature` 拿到函数参数注解并据此调用 Pydantic 验证

---

## 小节目录

1. [Pydantic 是什么，解决什么问题](#21-pydantic-是什么解决什么问题)
2. [BaseModel 核心机制](#22-basemodel-核心机制)
3. [验证器与字段约束](#23-验证器与字段约束)
4. [序列化与 model_dump](#24-序列化与-model_dump)
5. [JSON Schema 自动生成](#25-json-schema-自动生成)
6. [Annotated 与 Field：类型注解的进阶用法](#26-annotated-与-field类型注解的进阶用法)
7. [Pydantic v2 vs v1：Rust 内核](#27-pydantic-v2-vs-v1rust-内核)
8. [dataclass / TypedDict / BaseModel 对比](#28-dataclass--typeddict--basemodel-对比)
9. [为什么 FastAPI 选 Pydantic 而非 marshmallow](#29-为什么-fastapi-选-pydantic-而非-marshmallow)
10. [从注解到验证：inspect.signature 实战](#210-从注解到验证inspectsignature-实战)
11. [实践任务与产出](#211-实践任务与产出)
12. [小结与下一章衔接](#212-小结与下一章衔接)

---

## 2.1 Pydantic 是什么，解决什么问题

待补充：讲数据建模的普遍痛点（手写验证、类型与运行时脱节、文档与代码不同步），Pydantic 如何用"类型注解即契约"一举解决。

---

## 2.2 BaseModel 核心机制

### 2.2.1 定义与实例化

```python
from pydantic import BaseModel

class User(BaseModel):
    id: int
    name: str
    email: str

user = User(id=1, name="alice", email="a@x.com")
```

待补充：讲实例化时的自动类型转换（`id="1"` 会被转为 int）、验证失败抛 `ValidationError`。

### 2.2.2 嵌套模型

待补充：模型嵌套、列表/字典字段、自定义类型的验证传播。

---

## 2.3 验证器与字段约束

### 2.3.1 Field 约束

待补充：`Field(min_length=..., max_length=..., ge=..., le=..., pattern=...)` 的用法与对应的验证行为。

### 2.3.2 field_validator 与 model_validator

待补充：`@field_validator` 字段级验证、`@model_validator` 跨字段验证的写法与执行时机。

---

## 2.4 序列化与 model_dump

待补充：`model_dump()`、`model_dump_json()`、`exclude`/`include` 过滤、`by_alias`、与 v1 `.dict()` 的区别。

---

## 2.5 JSON Schema 自动生成

```python
print(User.model_json_schema())
```

待补充：展示输出结构，讲清 `properties`、`required`、`type` 字段如何对应 OpenAPI 的 components.schemas。**这是 FastAPI 自动文档的源头**，务必讲透。

---

## 2.6 Annotated 与 Field：类型注解的进阶用法

待补充：`Annotated[int, Field(gt=0)]` 的写法、为什么 FastAPI 推崇 `Annotated`（PEP 593）、与旧式 `Field(default=...)` 默认参数写法的对比。

---

## 2.7 Pydantic v2 vs v1：Rust 内核

待补充：`pydantic-core`（Rust）带来的性能提升（5–50x）、API 变化清单（`.dict()` → `.model_dump()` 等）、迁移要点。

---

## 2.8 dataclass / TypedDict / BaseModel 对比

待补充：用同一份数据分别用三种方式建模，对比验证能力、序列化、Schema 生成、性能，给出选型建议表。

| 维度 | dataclass | TypedDict | BaseModel |
|------|-----------|-----------|-----------|
| 运行时验证 | 无 | 无 | 有 |
| JSON Schema | 无 | 无 | 有 |
| 序列化控制 | 弱 | 无 | 强 |
| 性能 | 高 | 高 | 中（v2 已大幅提升） |

---

## 2.9 为什么 FastAPI 选 Pydantic 而非 marshmallow

待补充：从与 JSON Schema 的天然对接、类型注解原生集成、生态活跃度三个角度分析。

---

## 2.10 从注解到验证：inspect.signature 实战

```python
import inspect
from pydantic import BaseModel

class Item(BaseModel):
    name: str
    price: float

def create_item(item: Item, q: str | None = None):
    ...

sig = inspect.signature(create_item)
for name, param in sig.parameters.items():
    print(name, param.annotation)
```

待补充：演示如何拿到参数注解、如何区分 `Item`（请求体）与 `str | None`（查询参数）、如何调用 Pydantic 验证。**这是阶段 3 造轮子的核心技巧**。

---

## 2.11 实践任务与产出

### 任务 1：观察 Schema

定义 3 个模型，观察 `model_json_schema()` 输出，记录字段映射规律。

### 任务 2：注解驱动验证

写一个通用函数 `call_with_validation(func, path_params, query_params, body)`，根据 `inspect.signature` 自动验证入参并调用 `func`。

### 任务 3：三方式对比

用 dataclass / TypedDict / BaseModel 建模同一份数据，对比验证与序列化。

### 产出

- 参数验证脚本
- 本章笔记（≥ 700 行）

---

## 2.12 小结与下一章衔接

本章理解了类型系统。下一章把 ASGI 地基 + Pydantic 类型系统合起来，开始造轮子：实现路由与参数绑定，让 `@app.get("/users/{id}")` 真正跑起来。

---

!!! todo "待填充标记说明"
    本文件为大纲骨架，标注「待补充」处为后续要展开的内容点。每个待补充点都已规划好要讲的核心问题与示例方向，填充时直接展开即可达到 ≥ 700 行深度。**笔记深度与数量只增不减**，本骨架的小节结构在填充时只会扩充不会删减。