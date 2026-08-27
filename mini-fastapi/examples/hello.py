"""v0.0 示例：最简单的 mini-fastapi 应用。

运行：
    uv run uvicorn examples.hello:app --reload

当前 app 的 ASGI 入口尚未实现（阶段 1 填充），本示例先展示 API 声明形态。
"""

from mini_fastapi import MiniFastAPI

app = MiniFastAPI(title="Hello", version="0.0.0")


@app.get("/")
def root():
    return {"message": "hello, mini-fastapi"}


@app.get("/users/{user_id}")
def get_user(user_id: int):
    return {"user_id": user_id}