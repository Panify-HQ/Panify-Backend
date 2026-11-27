from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.v1.router import api_router
from app.core.config import settings
from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from app.api.v1 import inventory as inventario
from app.services.inventory import InventarioError



def create_application() -> FastAPI:
    application = FastAPI(
        title=settings.APP_NAME,
        version="1.0.0",
        debug=settings.DEBUG,
        description=(
            "API REST de Panify: gestión de pedidos, inventario, recibos "
            "y entregas de Distribuciones Oro Pan."
        ),
    )

    # Permite que el frontend (React + Vite) consuma la API desde orígenes autorizados
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    application.include_router(health_router)
    application.include_router(api_router, prefix=settings.API_V1_PREFIX)

    return application


app = create_application()
