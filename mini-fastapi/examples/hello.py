"""v0.3 示例：路由、参数绑定、请求体、response_model、status_code。

运行：
    uv run uvicorn examples.hello:app --reload

    GET /                         → {"message": "hello, mini-fastapi"}
    GET /users/42                 → {"user_id": 42}  (int 类型转换)
    GET /items?skip=5&limit=20    → {"skip": 5, "limit": 20, "q": null}
    POST /items (有效 JSON)        → 201, {"name": "...", "price": ...}
    POST /items (无效 JSON)        → 422 验证错误
    GET /error                    → 418 I'm a teapot
"""

from pydantic import BaseModel, Field

from mini_fastapi import HTTPException, MiniFastAPI

app = MiniFastAPI(title="Hello", version="0.3.0")


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
