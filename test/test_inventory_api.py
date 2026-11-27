from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_current_user
from app.api.v1.inventory import router
from app.infrastructure.database.base import Base
from app.infrastructure.database.session import get_db


def test_superadmin_can_manage_products_and_view_stock_alerts():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    with Session(engine) as db:
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
            rol=SimpleNamespace(nombre="Superadmin")
        )

        with TestClient(app) as client:
            create_response = client.post(
                "/api/v1/inventory/products",
                json={
                    "nombre": "Pan de prueba",
                    "precio": 1250,
                    "stockInicial": 0,
                },
            )
            alerts_response = client.get("/api/v1/inventory/alerts")

        assert create_response.status_code == 201
        assert alerts_response.status_code == 200
        assert [product["nombre"] for product in alerts_response.json()] == [
            "Pan de prueba"
        ]

    engine.dispose()
