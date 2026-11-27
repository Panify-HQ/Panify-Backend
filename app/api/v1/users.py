from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.api.dependencies import bearer_scheme, get_current_user
from app.api.openapi_examples import build_openapi_examples
from app.infrastructure.database.session import get_db
from app.models.usuario import Usuario
from app.schemas.user import (
    UserRole,
    UserResponse,
    UserUpdate,
    UsuarioCrear,
    UsuarioEstadoActualizar,
    UsuarioRespuesta,
)
from app.services.user_service import (
    UserAlreadyExistsError,
    UserNotFoundError,
    UserRoleNotFoundError,
    UserService,
    UserServiceError,
)

router = APIRouter(prefix="/users", tags=["Users"])


def require_super_admin(
    current_user: Usuario = Depends(get_current_user),
) -> Usuario:
    if current_user.rol.nombre != UserRole.SUPERADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para gestionar usuarios.",
        )

    return current_user


@router.post(
    "/",
    response_model=UsuarioRespuesta,
    status_code=status.HTTP_201_CREATED,
    summary="RF-001.1 / RF-002.2 - Registrar usuario",
    operation_id="rf_001_1_rf_002_2_registrar_usuario",
)
def registrar_usuario(
    datos: UsuarioCrear = Body(
        openapi_examples=build_openapi_examples(
            UsuarioCrear,
            {
                "cliente": "Registro de cliente",
                "panadero": "Registro de panadero",
                "domiciliario": "Registro de domiciliario",
                "administrador": "Registro de administrador",
            },
        )
    ),
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
):
    try:
        if datos.rol == UserRole.ADMINISTRADOR:
            if not isinstance(credentials, HTTPAuthorizationCredentials):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Se requiere autenticación para crear administradores.",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            usuario_actual = get_current_user(credentials, db)
            if usuario_actual.rol.nombre != UserRole.SUPERADMIN.value:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Solo un Superadmin puede crear administradores.",
                )
        elif datos.rol in (UserRole.PANADERO, UserRole.DOMICILIARIO):
            if not isinstance(credentials, HTTPAuthorizationCredentials):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Se requiere autenticación para crear personal.",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            usuario_actual = get_current_user(credentials, db)
            if usuario_actual.rol.nombre not in (
                UserRole.SUPERADMIN.value,
                UserRole.ADMINISTRADOR.value,
            ):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No tienes permisos para crear personal.",
                )

        return UserService.create_user(db, datos)

    except HTTPException:
        raise

    except UserRoleNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(error),
        ) from error

    except UserAlreadyExistsError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
    except UserServiceError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error


@router.get(
    "/",
    response_model=list[UserResponse],
    dependencies=[Depends(require_super_admin)],
    summary="RF-002.1 - Consultar y listar usuarios",
    operation_id="rf_002_1_listar_usuarios",
)
def list_users(
    role: UserRole | None = Query(
        default=None,
        openapi_examples={
            "clientes": {"summary": "Filtrar clientes", "value": "Cliente"},
            "administradores": {
                "summary": "Filtrar administradores",
                "value": "Administrador",
            },
        },
    ),
    is_active: bool | None = Query(
        default=None,
        openapi_examples={
            "activos": {"summary": "Usuarios activos", "value": True},
            "inactivos": {"summary": "Usuarios inactivos", "value": False},
        },
    ),
    skip: int = Query(
        default=0,
        ge=0,
        openapi_examples={
            "desde_inicio": {"summary": "Empezar desde el inicio", "value": 0},
            "siguiente_bloque": {
                "summary": "Saltar los primeros 20 usuarios",
                "value": 20,
            },
        },
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=100,
        openapi_examples={
            "veinte": {"summary": "Listar 20 usuarios", "value": 20},
            "cien": {"summary": "Listar hasta 100 usuarios", "value": 100},
        },
    ),
    db: Session = Depends(get_db),
):
    return UserService.list_users(
        db=db,
        role=role,
        is_active=is_active,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    dependencies=[Depends(require_super_admin)],
    summary="RF-002.1 - Consultar usuario por ID",
    operation_id="rf_002_1_consultar_usuario",
)
def get_user(
    user_id: int = Path(
        gt=0,
        openapi_examples={
            "usuario_1": {"summary": "Consultar usuario 1", "value": 1}
        },
    ),
    db: Session = Depends(get_db),
):
    try:
        return UserService.get_user(db, user_id)
    except UserNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        )


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
    dependencies=[Depends(require_super_admin)],
    summary="RF-002.3 - Actualizar información de usuario",
    operation_id="rf_002_3_actualizar_usuario",
)
def update_user(
    user_id: int = Path(
        gt=0,
        openapi_examples={
            "usuario_1": {"summary": "Actualizar usuario 1", "value": 1}
        },
    ),
    data: UserUpdate = Body(
        openapi_examples=build_openapi_examples(
            UserUpdate,
            {
                "actualizar_nombre": "Actualizar nombre",
                "actualizar_contacto": "Actualizar correo y teléfono",
                "actualizar_direccion": "Actualizar dirección",
            },
        )
    ),
    db: Session = Depends(get_db),
):
    try:
        return UserService.update_user(db, user_id, data)
    except UserNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        )
    except UserAlreadyExistsError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        )
    except UserServiceError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        )


@router.patch(
    "/{user_id}/status",
    response_model=UserResponse,
    summary="RF-002.3 - Actualizar estado de usuario",
    operation_id="rf_002_3_actualizar_estado_usuario",
)
def change_user_status(
    user_id: int = Path(
        gt=0,
        openapi_examples={
            "usuario_1": {"summary": "Cambiar estado del usuario 1", "value": 1}
        },
    ),
    data: UsuarioEstadoActualizar = Body(
        openapi_examples=build_openapi_examples(
            UsuarioEstadoActualizar,
            {
                "activar_usuario": "Activar usuario",
                "inactivar_usuario": "Inactivar usuario",
            },
        )
    ),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_super_admin),
):
    try:
        return UserService.change_status(
            db=db,
            user_id=user_id,
            is_active=data.estado == "Activo",
            current_user_id=current_user.idUsuario,
        )
    except UserNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        )
    except UserServiceError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        )
