"""OpenAPI 自动文档生成。

对应 FastAPI 源码的 `fastapi/openapi.py`。

设计哲学的集中体现：类型注解 → Pydantic schema → OpenAPI JSON → Swagger UI/ReDoc。

v0.5 实现：
- 遍历所有注册路由，从端点函数签名 + Pydantic 模型生成 OpenAPI 3.1 文档
- 挂载 /openapi.json、/docs（Swagger UI）、/redoc
"""

from __future__ import annotations

import inspect
from typing import Any, Callable, get_type_hints

from pydantic import BaseModel

from .dependencies import Depends
from .params import is_basemodel, is_optional, unpack_optional

_DOC_PATHS = {"/openapi.json", "/docs", "/redoc"}


def get_openapi(title: str, version: str, routes: list[Any]) -> dict[str, Any]:
    """生成 OpenAPI 3.1 文档字典。

    Args:
        title: 应用标题
        version: 应用版本
        routes: 路由列表

    Returns:
        符合 OpenAPI 3.1 规范的字典
    """
    paths: dict[str, dict] = {}
    components_schemas: dict[str, dict] = {}

    for route in routes:
        if route.path in _DOC_PATHS:
            continue
        path_item = _generate_path_item(route, components_schemas)
        if path_item:
            paths[route.path] = path_item

    doc: dict[str, Any] = {
        "openapi": "3.1.0",
        "info": {"title": title, "version": version},
        "paths": paths,
    }
    if components_schemas:
        doc["components"] = {"schemas": components_schemas}
    return doc


def _generate_path_item(route: Any, components_schemas: dict[str, dict]) -> dict[str, dict]:
    """为一条路由生成 paths 项（按 HTTP 方法组织）。"""
    path_item: dict[str, dict] = {}
    for method in route.methods:
        operation = _generate_operation(route, method, components_schemas)
        if operation:
            path_item[method.lower()] = operation
    return path_item


def _generate_operation(
    route: Any, method: str, components_schemas: dict[str, dict],
) -> dict[str, Any]:
    """生成一个 operation 对象。"""
    endpoint = route.endpoint
    sig = inspect.signature(endpoint)
    try:
        hints = get_type_hints(endpoint)
    except Exception:
        hints = {}

    parameters: list[dict[str, Any]] = []
    request_body: dict[str, Any] | None = None
    param_names_set = set(route.param_names)

    for name, param in sig.parameters.items():
        annotation = hints.get(name, param.annotation)
        default = param.default

        if isinstance(default, Depends):
            continue

        if is_basemodel(annotation):
            schema_ref = _get_schema_ref(annotation, components_schemas)
            request_body = {
                "required": True,
                "content": {"application/json": {"schema": schema_ref}},
            }
        elif name in param_names_set:
            parameters.append({
                "name": name,
                "in": "path",
                "required": True,
                "schema": _type_to_schema(annotation),
            })
        else:
            required = param.default is inspect.Parameter.empty
            parameters.append({
                "name": name,
                "in": "query",
                "required": required,
                "schema": _type_to_schema(annotation),
            })

    status_code = str(route.status_code or 200)
    if route.response_model is not None:
        response_schema = _get_schema_ref(route.response_model, components_schemas)
    else:
        response_schema = {"type": "object"}

    responses = {
        status_code: {
            "description": "Successful Response",
            "content": {"application/json": {"schema": response_schema}},
        }
    }

    operation: dict[str, Any] = {
        "summary": _get_summary(endpoint),
        "operationId": _get_operation_id(endpoint, route.path, method),
        "responses": responses,
    }
    if parameters:
        operation["parameters"] = parameters
    if request_body:
        operation["requestBody"] = request_body
    return operation


def _type_to_schema(annotation: Any) -> dict[str, Any]:
    """把 Python 类型注解转为 OpenAPI schema 片段。"""
    if annotation is inspect.Parameter.empty or annotation is None:
        return {}

    if is_optional(annotation):
        return _type_to_schema(unpack_optional(annotation))

    if annotation is int:
        return {"type": "integer"}
    if annotation is float:
        return {"type": "number"}
    if annotation is str:
        return {"type": "string"}
    if annotation is bool:
        return {"type": "boolean"}
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return {"type": "object"}
    return {}


def _get_schema_ref(
    model: type[BaseModel], components_schemas: dict[str, dict],
) -> dict[str, str]:
    """获取模型的 $ref，同时把 schema 存入 components.schemas。"""
    name = model.__name__
    if name not in components_schemas:
        schema = model.model_json_schema(ref_template="#/components/schemas/{model}")
        if "$defs" in schema:
            for def_name, def_schema in schema.pop("$defs").items():
                components_schemas[def_name] = def_schema
        components_schemas[name] = schema
    return {"$ref": f"#/components/schemas/{name}"}


def _get_summary(endpoint: Callable[..., Any]) -> str:
    """从端点函数获取摘要（docstring 首行或函数名）。"""
    doc = endpoint.__doc__
    if doc:
        return doc.strip().split("\n")[0]
    return endpoint.__name__.replace("_", " ").title()


def _get_operation_id(endpoint: Callable[..., Any], path: str, method: str) -> str:
    """生成 operationId（函数名 + 路径 + 方法）。"""
    clean_path = path.replace("/", "_").replace("{", "").replace("}", "")
    return f"{endpoint.__name__}{clean_path}_{method.lower()}"


_SWAGGER_HTML = """<!DOCTYPE html>
<html>
<head>
    <title>Swagger UI</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css">
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
    <script>
        window.onload = function() {
            SwaggerUIBundle({
                url: '/openapi.json',
                dom_id: '#swagger-ui',
            });
        };
    </script>
</body>
</html>"""


_REDOC_HTML = """<!DOCTYPE html>
<html>
<head>
    <title>ReDoc</title>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>body { margin: 0; padding: 0; }</style>
</head>
<body>
    <redoc spec-url='/openapi.json'></redoc>
    <script src="https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js"></script>
</body>
</html>"""


def setup_docs(app: Any) -> None:
    """为应用挂载文档路由 /openapi.json、/docs、/redoc。"""
    from .responses import Response

    def get_openapi_json() -> dict[str, Any]:
        return get_openapi(app.title, app.version, app.router.routes)

    def swagger_ui() -> Response:
        resp = Response(_SWAGGER_HTML, status_code=200)
        resp.media_type = "text/html; charset=utf-8"
        return resp

    def redoc() -> Response:
        resp = Response(_REDOC_HTML, status_code=200)
        resp.media_type = "text/html; charset=utf-8"
        return resp

    app.router.add_route("/openapi.json", get_openapi_json, methods=["GET"])
    app.router.add_route("/docs", swagger_ui, methods=["GET"])
    app.router.add_route("/redoc", redoc, methods=["GET"])
