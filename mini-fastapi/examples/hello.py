"""v0.1 示例：mini-fastapi 路由与路径参数。

运行：
    uv run uvicorn examples.hello:app --reload

    GET /            → {"message": "hello, mini-fastapi"}
    GET /users/42    → {"user_id": "42"}
    GET /items       → 404

注意：v0.1 路径参数均为 str，类型转换在 v0.2 实现。
"""

from mini_fastapi import MiniFastAPI

app = MiniFastAPI(title="Hello", version="0.1.0")


@app.get("/")
def root():
    return {"message": "hello, mini-fastapi"}


@app.get("/users/{user_id}")
def get_user(user_id: str):
    return {"user_id": user_id}


@app.get("/users/{user_id}/posts/{post_id}")
def get_post(user_id: str, post_id: str):
    return {"user_id": user_id, "post_id": post_id}


@app.post("/echo")
def echo():
    return {"echo": True}
