from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.infrastructure.database.session import get_db

from app.services.password_reset_service import (
    solicitar_codigo,
    restablecer_contrasena
)


router = APIRouter()


# Solicitud del código
class SolicitarCodigoRequest(BaseModel):
    correo: EmailStr


# Verificación y cambio de contraseña
class RestablecerContrasenaRequest(BaseModel):

    correo: EmailStr

    codigo: str = Field(
        min_length=6,
        max_length=6,
        pattern=r"^\d{6}$"
    )

    nueva_contrasena: str = Field(
        min_length=8,
        max_length=128
    )


class MensajeRespuesta(BaseModel):
    mensaje: str

@router.post(
    "/forgot-password",
    response_model=MensajeRespuesta,
    status_code=status.HTTP_202_ACCEPTED
)
def forgot_password(
    datos: SolicitarCodigoRequest,
    db: Session = Depends(get_db)
):

    resultado = solicitar_codigo(
        db=db,
        correo=str(datos.correo)
    )

    if resultado == "no_registrado":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El correo no está registrado en Panify."
        )

    if resultado == "espera":
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Ya solicitaste un código. Espera 60 segundos."
        )

    if resultado == "error_envio":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No fue posible enviar el correo. Inténtalo nuevamente."
        )

    return {
        "mensaje": "Código de recuperación enviado correctamente."
    }
@router.post(
    "/reset-password",
    response_model=MensajeRespuesta
)
def reset_password(
    datos: RestablecerContrasenaRequest,
    db: Session = Depends(get_db)
):

    try:
        restablecer_contrasena(
            db=db,
            correo=str(datos.correo),
            codigo=datos.codigo,
            nueva_contrasena=datos.nueva_contrasena
        )

        return {
            "mensaje": "Tu contraseña se ha actualizado correctamente."
        }

    except ValueError as error:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error)
        )