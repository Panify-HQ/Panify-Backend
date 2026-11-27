from datetime import date
from typing import NoReturn

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.infrastructure.database.session import get_db
from app.models.usuario import Usuario
from app.schemas.delivery import (
    DeliveryCustomerResponse,
    DeliveryHistoryResponse,
    DeliveryQueueResponse,
    DeliveryStatusResponse,
    DeliveryStatusUpdate,
)
from app.schemas.user import UserRole
from app.services.delivery_service import (
    DeliveryConflictError,
    DeliveryForbiddenError,
    DeliveryInvalidError,
    DeliveryNotFoundError,
    DeliveryService,
    DeliveryServiceError,
)

router = APIRouter(prefix="/deliveries", tags=["Deliveries"])


def require_roles(*allowed_roles: UserRole):
    allowed = {role.value for role in allowed_roles}

    def checker(current_user: Usuario = Depends(get_current_user)) -> Usuario:
        if current_user.rol.nombre not in allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        return current_user

    return checker


def _raise_delivery_error(error: DeliveryServiceError) -> NoReturn:
    if isinstance(error, DeliveryNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from error
    if isinstance(error, DeliveryForbiddenError):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN) from error
    if isinstance(error, DeliveryInvalidError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST) from error
    if isinstance(error, DeliveryConflictError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT) from error
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR) from error


@router.get(
    "/queue",
    response_model=DeliveryQueueResponse,
    summary="RF-006.1 - Gestionar prioridad de entregas",
    operation_id="rf_006_1_prioridad_entregas",
)
def get_delivery_queue(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(
        require_roles(
            UserRole.DOMICILIARIO,
            UserRole.PANADERO,
            UserRole.ADMINISTRADOR,
            UserRole.SUPERADMIN,
        )
    ),
):
    """Lista de entregas por antigüedad ."""
    try:
        return DeliveryService.get_priority_queue(db)
    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        ) from error


@router.get(
    "/history",
    response_model=DeliveryHistoryResponse,
    summary="RF-006.3 - Filtrar pedidos por fecha",
    operation_id="rf_006_3_filtrar_pedidos_por_fecha",
)
def filter_delivery_history(
    fechaInicio: date,
    fechaFin: date | None = Query(default=None),
    page: int = Query(default=1, gt=0),
    limiteRegistros: int = Query(default=50, gt=0, le=100),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(
        require_roles(
            UserRole.ADMINISTRADOR,
            UserRole.SUPERADMIN,
        )
    ),
):
    """Filtrar pedidos por fecha rango de fechas."""
    try:
        return DeliveryService.filter_history(
            db,
            fecha_inicio=fechaInicio,
            fecha_fin=fechaFin,
            page=page,
            page_size=limiteRegistros,
        )
    except DeliveryServiceError as error:
        _raise_delivery_error(error)
    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        ) from error


@router.get(
    "/{idPedido}/details",
    response_model=DeliveryCustomerResponse,
    summary="RF-006.4 - Visualizar información del cliente",
    operation_id="rf_006_4_informacion_cliente_pedido",
)
def get_order_details(
    idPedido: int = Path(gt=0),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(
        require_roles(
            UserRole.DOMICILIARIO,
            UserRole.PANADERO,
            UserRole.ADMINISTRADOR,
            UserRole.SUPERADMIN,
        )
    ),
):
    """Detalles de pedido."""
    try:
        return DeliveryService.get_customer_info(db, idPedido, current_user)
    except DeliveryServiceError as error:
        _raise_delivery_error(error)
    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        ) from error


@router.patch(
    "/{idPedido}/status",
    response_model=DeliveryStatusResponse,
    summary="RF-006.2 - Confirmar entrega",
    operation_id="rf_006_2_confirmar_entrega",
)
def update_order_status(
    data: DeliveryStatusUpdate,
    idPedido: int = Path(gt=0),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(
        require_roles(
            UserRole.DOMICILIARIO,
            UserRole.PANADERO,
            UserRole.ADMINISTRADOR,
            UserRole.SUPERADMIN,
        )
    ),
):
    """Actualizar estado del pedido."""
    try:
        return DeliveryService.update_order_status(
            db, idPedido, data.estadoPedido, current_user
        )
    except DeliveryServiceError as error:
        _raise_delivery_error(error)
    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        ) from error