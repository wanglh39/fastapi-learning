"""v0.5 示例：OpenAPI 自动文档 + 依赖注入。

运行：
    uv run uvicorn examples.hello:app --reload

    GET /openapi.json             → OpenAPI 3.1 文档
    GET /docs                     → Swagger UI
    GET /redoc                    → ReDoc
    GET /                         → {"message": "hello, mini-fastapi"}
    GET /users/42                 → {"user_id": 42}
    GET /items?skip=0&limit=10    → 分页列表
    POST /items                   → 201 创建
    GET /dep-items?skip=1         → Depends 注入 store + pagination
    GET /me?q=secret              → Depends 嵌套认证
    GET /session                  → yield 依赖（资源管理）
"""

from pydantic import BaseModel, Field

from mini_fastapi import Depends, HTTPException, MiniFastAPI

app = MiniFastAPI(title="Hello", version="0.5.0")


class ItemCreate(BaseModel):
    name: str = Field(min_length=1)
    price: float = Field(gt=0)


class ItemRead(BaseModel):
    name: str
    price: float


@app.get("/")
def root():
    return {"message": "hello, mini-fastapi"}


@app.get("/users/{user_id}")
def get_user(user_id: int):
    return {"user_id": user_id}


@app.get("/items")
def list_items(skip: int = 0, limit: int = 10, q: str | None = None):
    return {"skip": skip, "limit": limit, "q": q}


@app.post("/items", response_model=ItemRead, status_code=201)
def create_item(item: ItemCreate):
    return item


@app.get("/error")
def raise_error():
    raise HTTPException(status_code=418, detail="I'm a teapot")


# --- v0.4: 依赖注入 ---

_store = [
    {"id": 1, "name": "Widget", "price": 9.99},
    {"id": 2, "name": "Gadget", "price": 19.99},
    {"id": 3, "name": "Doohickey", "price": 29.99},
]


def get_store():
    """依赖：返回内存存储。"""
    return _store


def get_pagination(skip: int = 0, limit: int = 10):
    """依赖：分页参数（本身也是查询参数绑定）。"""
    return {"skip": skip, "limit": limit}


def get_token(q: str | None = None):
    """依赖：从查询参数提取 token。"""
    return q


def get_current_user(token: str = Depends(get_token)):
    """嵌套依赖：token → user。"""
    if token == "secret":
        return {"username": "alice", "role": "admin"}
    raise HTTPException(status_code=418, detail="I'm a teapot")


def get_session():
    """yield 依赖：模拟数据库会话。"""
    session = {"opened": True, "queries": []}
    yield session
    session["opened"] = False


@app.get("/dep-items")
def dep_items(
    store=Depends(get_store),
    pagination=Depends(get_pagination),
):
    """用 Depends 注入存储与分页参数。"""
    s = pagination["skip"]
    return store[s : s + pagination["limit"]]


@app.get("/me")
def me(user=Depends(get_current_user)):
    """嵌套 Depends：me → get_current_user → get_token。"""
    return user


@app.get("/session")
def use_session(session=Depends(get_session)):
    """yield Depends：注入会话，请求结束后自动清理。"""
    return {"opened": session["opened"], "queries": len(session["queries"])}
