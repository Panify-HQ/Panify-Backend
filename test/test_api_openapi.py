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
