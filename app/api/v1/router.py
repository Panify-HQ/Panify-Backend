from fastapi import APIRouter

from app.api.v1 import usuarios

api_router = APIRouter()

api_router.include_router(usuarios.router)
