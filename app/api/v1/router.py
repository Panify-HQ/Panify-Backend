from fastapi import APIRouter

from app.api.v1 import auth, usuarios
from app.api.v1.password_reset import router as password_reset_router

api_router = APIRouter()


api_router.include_router(
    password_reset_router,
    prefix="/auth",
    tags=["Recuperación de contraseña"]
)

api_router.include_router(auth.router)
api_router.include_router(usuarios.router)
