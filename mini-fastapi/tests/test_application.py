"""MiniFastAPI 应用层测试。

阶段 1 起逐步补充：ASGI 入口、路由分发、参数绑定、依赖注入等。
当前为占位，确保测试套件可被发现。
"""

from mini_fastapi import MiniFastAPI


def test_app_instance() -> None:
    """应用可被实例化并持有标题与版本。"""
    app = MiniFastAPI(title="Test", version="0.0.1")
    assert app.title == "Test"
    assert app.version == "0.0.1"
    assert app.router.routes == []