from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.infrastructure.database.session import get_db
from app.schemas.usuario import UsuarioCrear, UsuarioRespuesta
from app.services.usuario_service import crear_usuario

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])


@router.post("/", response_model=UsuarioRespuesta, status_code=status.HTTP_201_CREATED)
def registrar_usuario(datos: UsuarioCrear, db: Session = Depends(get_db)):
    try:
        usuario = crear_usuario(
            db=db,
            nombre=datos.nombre,
            apellido=datos.apellido,
            correo=datos.correo,
            contrasena=datos.contrasena,
            telefono=datos.telefono,
            rol_id=1,
        )

        return usuario

    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No fue posible registrar el usuario.",
        )
