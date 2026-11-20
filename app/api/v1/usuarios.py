from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.database.session import get_db
from app.models.rol import Rol
from app.schemas.usuario import UsuarioCrear, UsuarioRespuesta
from app.services.usuario_service import crear_usuario

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])


@router.post("/", response_model=UsuarioRespuesta, status_code=status.HTTP_201_CREATED)
def registrar_usuario(datos: UsuarioCrear, db: Session = Depends(get_db)):
    try:
        rol_cliente = db.scalar(select(Rol).where(Rol.nombre == "Cliente"))
        if rol_cliente is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="El rol Cliente no está configurado.",
            )

        usuario = crear_usuario(
            db=db,
            nombre=datos.nombre,
            apellido=datos.apellido,
            correo=datos.correo,
            contrasena=datos.contrasena,
            telefono=datos.telefono,
            direccion=datos.direccion,
            rol_id=rol_cliente.idRol,
        )

        return usuario

    except HTTPException:
        raise

    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No fue posible registrar el usuario.",
        )
