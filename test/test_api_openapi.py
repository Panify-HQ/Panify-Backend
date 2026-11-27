from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.v1.router import api_router


def test_openapi_operations_have_unique_rf_names_except_technical_routes():
    app = FastAPI()
    app.include_router(health_router)
    app.include_router(api_router, prefix="/api/v1")

    operations = [
        (method, path, operation)
        for path, path_item in app.openapi()["paths"].items()
        for method, operation in path_item.items()
        if method in {"get", "post", "put", "patch", "delete"}
    ]
    operation_ids = [operation["operationId"] for _, _, operation in operations]
    technical_routes = {
        ("get", "/health"),
        ("get", "/health/ready"),
        ("post", "/api/v1/auth/logout"),
    }

    assert len(operation_ids) == len(set(operation_ids))

    for method, path, operation in operations:
        if (method, path) in technical_routes:
            assert not operation["summary"].startswith("RF-")
        else:
            assert operation["summary"].startswith("RF-")
            assert operation["operationId"].startswith("rf_")


def test_schema_examples_are_exposed_as_selectable_request_examples():
    app = FastAPI()
    app.include_router(api_router, prefix="/api/v1")
    openapi = app.openapi()
    checked_examples = 0

    for path_item in openapi["paths"].values():
        for operation in path_item.values():
            request_body = operation.get("requestBody", {})
            content = request_body.get("content", {}).get("application/json", {})
            schema_ref = content.get("schema", {}).get("$ref")
            if schema_ref is None:
                continue

            schema_name = schema_ref.rsplit("/", 1)[-1]
            schema_examples = openapi["components"]["schemas"][schema_name].get(
                "examples", []
            )
            if not schema_examples:
                continue

            body_examples = content.get("examples", {})
            assert [example["value"] for example in body_examples.values()] == (
                schema_examples
            )
            checked_examples += len(body_examples)

    assert checked_examples > 0


def test_all_path_and_query_parameters_have_openapi_examples():
    app = FastAPI()
    app.include_router(api_router, prefix="/api/v1")
    openapi = app.openapi()
    checked_parameters = 0

    for path, path_item in openapi["paths"].items():
        path_parameters = set()
        for method, operation in path_item.items():
            if method not in {"get", "post", "put", "patch", "delete"}:
                continue
            for parameter in operation.get("parameters", []):
                if parameter["in"] not in {"path", "query"}:
                    continue
                assert parameter.get("examples"), (
                    f"{method.upper()} {path} parameter {parameter['name']} "
                    "has no OpenAPI examples."
                )
                checked_parameters += 1
                if parameter["in"] == "path":
                    path_parameters.add(parameter["name"])

        placeholders = {
            segment[1:-1]
            for segment in path.split("/")
            if segment.startswith("{") and segment.endswith("}")
        }
        assert placeholders <= path_parameters

    assert checked_parameters > 0
