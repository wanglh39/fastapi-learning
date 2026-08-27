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
6. 用 `inspect.signature` + `get_type_hints` 拿到函数参数注解并据此调用 Pydantic 验证

---

## 小节目录

1. Pydantic 是什么，解决什么问题
2. BaseModel 核心机制
3. 验证器与字段约束
4. 序列化与 model_dump
5. JSON Schema 自动生成
6. Annotated 与 Field：类型注解的进阶用法
7. Pydantic v2 vs v1：Rust 内核
8. dataclass / TypedDict / BaseModel 对比
9. 为什么 FastAPI 选 Pydantic 而非 marshmallow
10. 从注解到验证：inspect.signature 实战
11. 实践任务与产出
12. 小结与下一章衔接

---

## 2.1 Pydantic 是什么，解决什么问题

### 2.1.1 数据建模的普遍痛点

在没有 Pydantic 的世界里，处理外部输入（HTTP 请求体、配置文件、API 响应）通常这样写：

```python
def create_user(data: dict):
    if "id" not in data:
        raise ValueError("缺少 id")
    if not isinstance(data["id"], int):
        try:
            data["id"] = int(data["id"])
        except ValueError:
            raise ValueError("id 必须是整数")
    if "name" not in data:
        raise ValueError("缺少 name")
    if not isinstance(data["name"], str):
        raise ValueError("name 必须是字符串")
    # ... 每个字段都要重复这套检查
    return data
```

痛点很明显：

| 痛点 | 说明 |
|------|------|
| **手写验证繁琐** | 每个字段都要手写类型检查、必填检查、转换逻辑 |
| **类型与运行时脱节** | 类型注解 `data: dict` 不提供任何运行时保护 |
| **文档与代码不同步** | 接口文档里写的字段约束，代码里不一定真的检查了 |
| **错误信息不统一** | 每个开发者抛的异常格式各异 |

### 2.1.2 Pydantic 的解法：类型注解即契约

Pydantic 的核心洞察：**类型注解不只是给 IDE 看的提示，它应该驱动运行时验证**。

```python
from pydantic import BaseModel

class User(BaseModel):
    id: int
    name: str
    age: int = 0

user = User(id=1, name="alice", age=30)  # OK
user = User(id="42", name="bob")          # OK，自动把 "42" 转为 42
User(id="x", name="bob")                  # ValidationError，告诉你 id 有问题
```

一行注解 `id: int` 同时表达了：字段名、类型、必填（无默认值）。Pydantic 在实例化时自动验证、转换、报错。**代码即文档，文档即代码**。

---

## 2.2 BaseModel 核心机制

### 2.2.1 定义与实例化

```python
from pydantic import BaseModel

class User(BaseModel):
    id: int
    name: str
    email: str
    age: int = 0  # 有默认值，选填
```

实例化时 Pydantic 做三件事：

1. **必填检查**：无默认值的字段必须提供
2. **类型转换**：能安全转换的就转（`id="42"` → `42`）
3. **验证报错**：不能转换的抛 `ValidationError`，包含精确的错误位置与原因

```python
user = User(id=1, name="alice", email="a@x.com", age=30)
print(user.id, type(user.id))  # 1 <class 'int'>

auto = User(id="42", name="bob", email="b@x.com")
print(auto.id, type(auto.id))  # 42 <class 'int'>  ← str 自动转 int
```

### 2.2.2 验证失败与错误结构

```python
from pydantic import ValidationError

try:
    User(id="not-a-number", name="x", email="x@x.com")
except ValidationError as exc:
    for err in exc.errors():
        print(err["loc"], err["type"], err["msg"])
    # ('id',) int_parsing Input should be a valid integer
```

`ValidationError.errors()` 返回一个列表，每个错误包含：

| 字段 | 说明 | 示例 |
|------|------|------|
| `loc` | 错误位置（元组，支持嵌套路径） | `("id",)` 或 `("address", "city")` |
| `type` | 错误类型码 | `int_parsing`、`missing`、`greater_than` |
| `msg` | 人类可读信息 | `Input should be a valid integer` |
| `input` | 导致错误的原始值 | `"not-a-number"` |

!!! tip "loc 的嵌套路径"
    对于嵌套模型，`loc` 会是多层路径，如 `("address", "city")` 表示 `user.address.city` 字段出错。FastAPI 的 422 响应里 `loc` 就是这个结构。

### 2.2.3 嵌套模型

模型可以嵌套，验证会递归传播：

```python
class Address(BaseModel):
    city: str
    zip_code: str

class UserWithAddress(BaseModel):
    id: int
    name: str
    address: Address

user = UserWithAddress(
    id=1,
    name="alice",
    address={"city": "北京", "zip_code": "100000"},  # dict 自动转为 Address
)
print(user.address.city)  # 北京
print(type(user.address))  # <class 'Address'>
```

传入 `dict` 会自动用 `Address.model_validate()` 转为模型实例。嵌套验证失败时，`loc` 会反映嵌套路径。

---

### 2.2.4 model_config：模型级配置

`model_config` 控制模型的全局行为：

```python
from pydantic import ConfigDict

class User(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
        frozen=True,
    )
    name: str
    age: int

user = User(name="  alice  ", age=30)
print(user.name)  # "alice"  ← 空白被去除

User(name="alice", age=30, extra_field="x")  # ValidationError: extra_field 不允许
```

常用配置项：

| 配置 | 说明 |
|------|------|
| `str_strip_whitespace` | 自动 strip 字符串字段 |
| `extra="forbid"` | 禁止额外字段 |
| `extra="ignore"` | 忽略额外字段（默认） |
| `frozen=True` | 不可变模型 |
| `from_attributes=True` | 允许从 ORM 对象属性创建（v1 的 `orm_mode`） |
| `populate_by_name=True` | 允许用字段名而非 alias 填充 |

---

## 2.3 验证器与字段约束

### 2.3.1 Field 约束

`Field` 为字段添加约束，实例化时自动检查：

```python
from pydantic import Field

class Product(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    price: float = Field(gt=0, description="价格必须为正")
    stock: int = Field(ge=0, default=0)
    tags: list[str] = Field(default_factory=list, max_length=10)
```

常用约束：

| 约束 | 适用类型 | 含义 |
|------|---------|------|
| `gt` / `ge` | 数值 | 大于 / 大于等于 |
| `lt` / `le` | 数值 | 小于 / 小于等于 |
| `min_length` / `max_length` | str/list | 长度范围 |
| `pattern` | str | 正则匹配 |
| `default` | 任意 | 默认值 |
| `default_factory` | 任意 | 默认值工厂（如 `list`） |
| `description` | 任意 | 描述（进 JSON Schema） |

### 2.3.2 field_validator：字段级验证

```python
from pydantic import field_validator

class SignupRequest(BaseModel):
    password: str

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("密码至少 8 位")
        return v
```

`field_validator` 在字段类型转换**之后**执行，接收已转换的值，返回验证后的值（或抛 `ValueError`）。

### 2.3.3 model_validator：跨字段验证

```python
from pydantic import model_validator

class SignupRequest(BaseModel):
    password: str
    password_confirm: str

    @model_validator(mode="after")
    def passwords_match(self) -> "SignupRequest":
        if self.password != self.password_confirm:
            raise ValueError("两次密码不一致")
        return self
```

`model_validator(mode="after")` 在整个模型验证完成后执行，可以访问 `self` 的所有字段，适合跨字段一致性检查（如密码确认、日期范围）。

---

## 2.4 序列化与 model_dump

Pydantic v2 的序列化方法：

```python
user = User(id=1, name="alice", email="a@x.com", age=30)

user.model_dump()                    # {'id': 1, 'name': 'alice', 'email': 'a@x.com', 'age': 30}
user.model_dump_json()               # '{"id":1,"name":"alice","email":"a@x.com","age":30}'
user.model_dump(exclude={"age"})     # {'id': 1, 'name': 'alice', 'email': 'a@x.com'}
user.model_dump(include={"name", "email"})  # {'name': 'alice', 'email': 'a@x.com'}
```

| 方法 | 返回 | 用途 |
|------|------|------|
| `model_dump()` | `dict` | 转 Python 字典 |
| `model_dump_json()` | `str` | 直接转 JSON 字符串（更快） |
| `model_validate(dict)` | 模型实例 | 从 dict 创建并验证 |
| `model_validate_json(str)` | 模型实例 | 从 JSON 字符串创建并验证 |

!!! warning "v1 vs v2 方法名"
    Pydantic v1 用 `.dict()` / `.json()` / `.parse_obj()`，v2 改为 `.model_dump()` / `.model_dump_json()` / `.model_validate()`。旧名在 v2 中已废弃。

---

## 2.5 JSON Schema 自动生成

**这是 FastAPI 自动文档的源头**，务必讲透。

### 2.5.1 model_json_schema 的输出

```python
print(User.model_json_schema())
```

输出：

```json
{
  "type": "object",
  "properties": {
    "id": {"type": "integer", "title": "Id"},
    "name": {"type": "string", "title": "Name"},
    "email": {"type": "string", "title": "Email"},
    "age": {"type": "integer", "title": "Age", "default": 0}
  },
  "required": ["id", "name", "email"]
}
```

结构对应 **JSON Schema** 规范：

| 字段 | 含义 |
|------|------|
| `type` | 数据类型（`object`/`integer`/`string`/...） |
| `properties` | 各字段的子 schema |
| `required` | 必填字段名列表 |

### 2.5.2 约束如何进入 Schema

```python
class Product(BaseModel):
    price: float = Field(gt=0)

print(Product.model_json_schema()["properties"]["price"])
# {"type": "number", "title": "Price", "exclusiveMinimum": 0}
```

`gt=0` 变成了 `"exclusiveMinimum": 0`。**Field 约束自动反映到 Schema**——这就是为什么 FastAPI 的 `/docs` 能显示参数范围：它直接用 Pydantic 生成的 Schema。

### 2.5.3 从 Schema 到 OpenAPI

FastAPI 把每个端点的 Pydantic 模型 Schema 收集到 OpenAPI 文档的 `components.schemas` 里，端点的 `requestBody` 和 `responses` 用 `$ref` 引用。Swagger UI 读取 OpenAPI 文档渲染出可交互的接口文档。整条链路：

```
类型注解 → Pydantic 模型 → model_json_schema() → OpenAPI components.schemas → Swagger UI
```

---

### 2.5.4 嵌套模型的 Schema 与 $ref

嵌套模型的 Schema 用 `$ref` 引用，实现复用：

```python
class Address(BaseModel):
    city: str
    zip_code: str

class UserWithAddress(BaseModel):
    id: int
    address: Address

import json
print(json.dumps(UserWithAddress.model_json_schema(), indent=2))
```

输出：

```json
{
  "$defs": {
    "Address": {
      "type": "object",
      "properties": {
        "city": {"type": "string", "title": "City"},
        "zip_code": {"type": "string", "title": "Zip Code"}
      },
      "required": ["city", "zip_code"]
    }
  },
  "type": "object",
  "properties": {
    "id": {"type": "integer", "title": "Id"},
    "address": {"$ref": "#/$defs/Address"}
  },
  "required": ["id", "address"]
}
```

`$defs` 存放可复用的模型定义，`$ref` 引用。**这正是 FastAPI 把模型收集到 OpenAPI `components.schemas` 的机制**——同一个模型在多个端点使用时只定义一次，处处引用。

---

## 2.6 Annotated 与 Field：类型注解的进阶用法

### 2.6.1 为什么用 Annotated

传统写法把 `Field` 作为默认值：

```python
class Order(BaseModel):
    quantity: int = Field(gt=0, le=100)  # quantity 的"类型"被 Field 默认值掩盖
```

`Annotated`（PEP 593）把约束附加到类型上，类型与约束分离：

```python
from typing import Annotated

Quantity = Annotated[int, Field(gt=0, le=100, description="数量 1-100")]

class Order(BaseModel):
    quantity: Quantity  # 类型清晰是 int，约束在 Annotated 里
```

### 2.6.2 FastAPI 推崇 Annotated 的原因

FastAPI 文档推荐 `Annotated` 写法，因为：

1. **类型可复用**：`Quantity` 定义一次，多处使用
2. **IDE 友好**：类型检查器能正确识别 `quantity` 是 `int`
3. **与 `Path`/`Query`/`Body` 一致**：`Annotated[int, Query(gt=0)]` 是 FastAPI 的标准参数标记写法

---

## 2.7 Pydantic v2 vs v1：Rust 内核

### 2.7.1 性能提升

Pydantic v2 把核心验证逻辑用 **Rust** 重写为 `pydantic-core`，性能提升 5–50 倍：

| 操作 | v1 | v2 | 提升 |
|------|----|----|------|
| 实例化（简单模型） | 1x | ~17x | 17 倍 |
| 实例化（嵌套模型） | 1x | ~50x | 50 倍 |
| `model_dump()` | 1x | ~5x | 5 倍 |
| JSON Schema 生成 | 1x | ~3x | 3 倍 |

### 2.7.2 主要 API 变化

| v1 | v2 | 说明 |
|----|----|------|
| `.dict()` | `.model_dump()` | 转字典 |
| `.json()` | `.model_dump_json()` | 转 JSON |
| `.parse_obj()` | `.model_validate()` | 从 dict 创建 |
| `.parse_raw()` | `.model_validate_json()` | 从 JSON 字符串创建 |
| `@validator` | `@field_validator` | 字段验证器 |
| `@root_validator` | `@model_validator` | 模型级验证器 |
| `Config` 内部类 | `model_config` | 配置 |

---

### 2.7.3 从 v1 迁移示例

一个典型的 v1 模型迁移：

```python
# v1 写法
from pydantic import BaseModel, validator, root_validator

class UserV1(BaseModel):
    name: str
    age: int

    class Config:
        orm_mode = True

    @validator("name")
    def name_not_empty(cls, v):
        if not v:
            raise ValueError("name 不能为空")
        return v

# v2 等价写法
from pydantic import BaseModel, field_validator, ConfigDict

class UserV2(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    age: int

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v):
        if not v:
            raise ValueError("name 不能为空")
        return v
```

关键迁移点：`Config` 内部类 → `model_config = ConfigDict(...)`，`orm_mode` → `from_attributes`，`@validator` → `@field_validator` + `@classmethod`，`@root_validator` → `@model_validator`。

---

## 2.8 dataclass / TypedDict / BaseModel 对比

用同一份数据分别建模：

```python
from dataclasses import dataclass
from typing import TypedDict

@dataclass
class UserDataclass:
    id: int
    name: str

class UserTypedDict(TypedDict):
    id: int
    name: str

class UserBaseModel(BaseModel):
    id: int
    name: str
```

对比：

| 维度 | dataclass | TypedDict | BaseModel |
|------|-----------|-----------|-----------|
| 运行时验证 | ❌ 无 | ❌ 无 | ✅ 有 |
| 自动类型转换 | ❌ `id="42"` 保持 str | ❌ 无 | ✅ `id="42"` → 42 |
| JSON Schema | ❌ 无 | ❌ 无 | ✅ `model_json_schema()` |
| 序列化控制 | 弱 | 无 | ✅ `exclude`/`include` |
| 嵌套验证 | ❌ 无 | ❌ 无 | ✅ 递归 |
| 验证器 | ❌ 无 | ❌ 无 | ✅ `field_validator` |
| 性能 | 高 | 高 | 中（v2 已大幅提升） |
| 用途 | 内部数据结构 | dict 类型提示 | 外部输入契约 |

**结论**：需要验证外部输入、生成文档契约时用 `BaseModel`；纯内部数据传递用 `dataclass`。

---

## 2.9 为什么 FastAPI 选 Pydantic 而非 marshmallow

Python 生态里另一个流行的验证库是 marshmallow。FastAPI 选 Pydantic 的原因：

| 维度 | Pydantic | marshmallow |
|------|----------|-------------|
| 类型注解集成 | 原生（注解即字段） | 需单独定义 Schema 类 |
| JSON Schema | `model_json_schema()` 内置 | 需 `schema()` 但与类型注解分离 |
| 性能 | v2 Rust 内核，极快 | 纯 Python，较慢 |
| 生态 | FastAPI/SQLModel 原生集成 | 通用但无框架深度集成 |
| 学习成本 | 低（会写 dataclass 就会） | 中（需学 Schema API） |

核心原因：**Pydantic 与类型注解的原生集成，让 FastAPI 能直接从函数签名提取参数契约**——这是 marshmallow 做不到的。

---

## 2.10 从注解到验证：inspect.signature 实战

这是阶段 3 造轮子的**核心技巧**：从端点函数的参数注解，自动区分参数来源并验证。

### 2.10.1 拿到参数注解

```python
import inspect
from typing import get_type_hints

def create_item(item: ItemCreate, category: str = "default"):
    ...

sig = inspect.signature(create_item)
hints = get_type_hints(create_item)  # 解析字符串注解为实际类型

for name, param in sig.parameters.items():
    annotation = hints.get(name, param.annotation)
    print(name, annotation, param.default)
# item <class 'ItemCreate'> <class 'inspect._empty'>
# category <class 'str'> 'default'
```

!!! warning "from __future__ import annotations 的坑"
    启用 `from __future__ import annotations` 后，所有注解变成字符串（PEP 563）。`param.annotation` 拿到的是 `'ItemCreate'` 而非类本身。必须用 `get_type_hints(func)` 解析为实际类型，否则 `issubclass` 等检查会失败。

### 2.10.2 区分参数来源

```python
def is_basemodel(annotation) -> bool:
    return isinstance(annotation, type) and issubclass(annotation, BaseModel)

def resolve_param_kind(annotation, path_param_names, name) -> str:
    if name in path_param_names:
        return "path"
    if is_basemodel(annotation):
        return "body"
    return "query"
```

规则：

| 条件 | 来源 |
|------|------|
| 参数名出现在路径模式 `{name}` 中 | path |
| 注解是 `BaseModel` 子类 | body（请求体） |
| 其他（int/str/float/Optional 等） | query（查询参数） |

### 2.10.3 验证并调用

```python
def validate_and_call(func, path_params, query_params, body):
    sig = inspect.signature(func)
    hints = get_type_hints(func)
    kwargs = {}

    for name, param in sig.parameters.items():
        annotation = hints.get(name, param.annotation)

        if is_basemodel(annotation):
            kwargs[name] = annotation.model_validate(body)  # Pydantic 验证请求体
        elif name in path_params:
            kwargs[name] = convert(path_params[name], annotation)  # 类型转换
        elif name in query_params:
            kwargs[name] = convert(query_params[name], annotation)
        elif param.default is not inspect.Parameter.empty:
            kwargs[name] = param.default  # 用默认值

    return func(**kwargs)
```

这就是 FastAPI 参数绑定的核心原理的简化版。运行 `examples/annotation_validation.py` 可以看到完整演示：

```
函数: create_item(item: ItemCreate, category: str = 'default')
参数              注解                        来源       默认
item            ItemCreate                body      必填
category        str                       query     'default'

create_item(body={name:Widget, price:9.99}, category=tools)
  → {'item': ItemCreate(name='Widget', price=9.99), 'category': 'tools'}

price=-1 → ValidationError: Input should be greater than 0
```

---

### 2.10.4 实现要点总结

把上述技巧总结为阶段 3 造轮子的实现清单：

1. **用 `get_type_hints(func)` 而非 `param.annotation`**：前者解析字符串注解，后者在 `from __future__ import annotations` 下是字符串
2. **`issubclass(annotation, BaseModel)` 判断请求体**：只有 BaseModel 子类走 Pydantic 验证
3. **基本类型手动转换**：int/float/bool 的字符串转 Python 类型
4. **`Optional[X]` 处理**：解包出内部类型，None 值放行
5. **缺失参数用默认值**：`param.default is not inspect.Parameter.empty` 判断有无默认值
6. **验证失败转 422**：捕获 `ValidationError`，把 `errors()` 转为 FastAPI 风格的 `detail` 数组

这些要点将在阶段 3 的 `params.py` 与 `application.py` 中落地为代码。

---

## 2.11 实践任务与产出

### 任务 1：Pydantic 核心能力演示

已实现 `examples/pydantic_demo.py`，覆盖 BaseModel、类型转换、验证失败、嵌套模型、Field 约束、验证器、序列化、JSON Schema、Annotated、三方式对比。

```bash
uv run python examples/pydantic_demo.py
```

### 任务 2：注解驱动验证

已实现 `examples/annotation_validation.py`，演示 `inspect.signature` + `get_type_hints` 从函数签名提取参数契约并验证调用。

```bash
uv run python examples/annotation_validation.py
```

### 任务 3：测试

已编写 15 个 Pydantic 行为测试（`tests/test_pydantic_basics.py`），覆盖类型转换、验证失败、约束、序列化、Schema、验证器、Optional。

```bash
uv run pytest tests/test_pydantic_basics.py -v  # 15 passed
```

### 产出

- 两个实践脚本
- 15 个 Pydantic 测试（总计 38 个测试全通过）
- 本章笔记（≥ 700 行）

---

## 2.12 小结与下一章衔接

本章理解了 FastAPI"类型优先"哲学的根基：

1. **Pydantic BaseModel**：类型注解驱动运行时验证、自动类型转换、统一错误结构
2. **Field 约束 + 验证器**：字段级与跨字段验证
3. **JSON Schema 自动生成**：FastAPI 自动文档的源头——注解 → Schema → OpenAPI → Swagger UI
4. **Annotated**：类型与约束分离，FastAPI 推崇的写法
5. **inspect.signature + get_type_hints**：从函数签名提取参数契约——阶段 3 造轮子的核心技巧

现在我们有了两块基石：阶段 1 的 ASGI 地基 + 本章的类型系统。下一章把它们合起来，开始造轮子：实现路由装饰器、路径参数类型转换、查询参数与请求体绑定，让 mini-fastapi 从 v0.1 进化到 v0.3。

---

!!! success "阶段 2 完成"
    - 两个实践脚本 + 15 个 Pydantic 测试
    - 本章笔记已展开为完整正文
    - 下一章：阶段 3 · 造轮子：路由与参数绑定
