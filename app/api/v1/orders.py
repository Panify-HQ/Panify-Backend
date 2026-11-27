from datetime import date
from typing import NoReturn

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.infrastructure.database.session import get_db
from app.models.usuario import Usuario
from app.schemas.order import (
    OrderCreate,
    OrderCreateResponse,
    OrderDetailResponse,
    OrderListItem,
    OrderListResponse,
    OrderState,
    OrderStatusResponse,
    OrderStatusUpdate,
)
from app.schemas.receipt import ReceiptCreationResponse
from app.schemas.user import UserRole
from app.services.order_service import (
    OrderConflictError,
    OrderForbiddenError,
    OrderInvalidError,
    OrderNotFoundError,
    OrderService,
    OrderServiceError,
)
from app.services.receipt_service import (
    OrderNotFoundError as ReceiptOrderNotFoundError,
    ReceiptConflictError,
    ReceiptService,
)

router = APIRouter(prefix="/orders", tags=["Orders"])
ROLES_GESTION = ("Administrador", "Panadero", "Superadmin")

def _require_roles(current_user: Usuario, allowed_roles: tuple[str, ...]) -> None:
    if current_user.rol.nombre not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para realizar esta acción.",
        )


def _raise_order_error(error: OrderServiceError) -> NoReturn:
    if isinstance(error, OrderNotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    if isinstance(error, OrderForbiddenError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(error),
        ) from error
    if isinstance(error, OrderInvalidError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error
    if isinstance(error, OrderConflictError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Error interno al procesar el pedido.",
    ) from error


def _raise_database_error(db: Session, error: SQLAlchemyError) -> NoReturn:
    db.rollback()
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Error interno de base de datos al procesar el pedido.",
    ) from error


@router.post(
    "",
    response_model=OrderCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_order(
    data: OrderCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(
        current_user,
        (
            UserRole.CLIENTE.value,
            UserRole.ADMINISTRADOR.value,
            UserRole.SUPERADMIN.value,
        ),
    )
    try:
        return OrderService.create_order(db, data, current_user)
    except OrderServiceError as error:
        _raise_order_error(error)
    except SQLAlchemyError as error:
        _raise_database_error(db, error)


@router.get("", response_model=OrderListResponse)   
def list_orders(
    estadoPedido: OrderState | None = Query(default=None),
    filtroTexto: str | None = Query(default=None, max_length=100),
    page: int = Query(default=1, gt=0),
    page_size: int = Query(default=20, gt=0, le=100),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    try:
        return OrderService.list_orders(
            db,
            current_user,
            estado=estadoPedido,
            text_filter=filtroTexto,
            page=page,
            page_size=page_size,
        )
    except OrderServiceError as error:
        _raise_order_error(error)
    except SQLAlchemyError as error:
        _raise_database_error(db, error)


@router.get("/dispatch-queue", response_model=list[OrderListItem])
def get_dispatch_queue(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(
        current_user,
        (
            UserRole.PANADERO.value,
            UserRole.DOMICILIARIO.value,
            UserRole.ADMINISTRADOR.value,
            UserRole.SUPERADMIN.value,
        ),
    )
    try:
        return OrderService.dispatch_queue(db)
    except SQLAlchemyError as error:
        _raise_database_error(db, error)


@router.get("/history/filter", response_model=OrderListResponse)
def filter_order_history(
    fechaInicio: date,
    fechaFin: date,
    page: int = Query(default=1, gt=0),
    page_size: int = Query(default=20, gt=0, le=100),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    try:
        return OrderService.history_filter(
            db,
            current_user,
            fecha_inicio=fechaInicio,
            fecha_fin=fechaFin,
            page=page,
            page_size=page_size,
        )
    except OrderServiceError as error:
        _raise_order_error(error)
    except SQLAlchemyError as error:
        _raise_database_error(db, error)


@router.get("/{idPedido}", response_model=OrderDetailResponse)
def get_order_detail(
    idPedido: int = Path(gt=0),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    try:
        return OrderService.get_order_detail(db, idPedido, current_user)
    except OrderServiceError as error:
        _raise_order_error(error)
    except SQLAlchemyError as error:
        _raise_database_error(db, error)


@router.patch("/{idPedido}/cancel", response_model=OrderStatusResponse)
def cancel_order(
    idPedido: int = Path(gt=0),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(
        current_user,
        (
            UserRole.CLIENTE.value,
            UserRole.ADMINISTRADOR.value,
            UserRole.SUPERADMIN.value,
        ),
    )
    try:
        return OrderService.cancel_order(db, idPedido, current_user)
    except OrderServiceError as error:
        _raise_order_error(error)
    except SQLAlchemyError as error:
        _raise_database_error(db, error)


@router.patch("/{idPedido}/status", response_model=OrderStatusResponse)
def update_order_status(
    data: OrderStatusUpdate,
    idPedido: int = Path(gt=0),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    _require_roles(
        current_user,
        (
            UserRole.PANADERO.value,
            UserRole.DOMICILIARIO.value,
            UserRole.ADMINISTRADOR.value,
            UserRole.SUPERADMIN.value,
        ),
    )
    try:
        return OrderService.update_status(db, idPedido, data, current_user)
    except OrderServiceError as error:
        _raise_order_error(error)
    except SQLAlchemyError as error:
        _raise_database_error(db, error)


@router.post(
    "/{order_id}/confirm",
    response_model=ReceiptCreationResponse,
    status_code=status.HTTP_201_CREATED,
)
def confirm_order(
    order_id: int = Path(gt=0),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    if current_user.rol.nombre not in (
        UserRole.ADMINISTRADOR.value,
        UserRole.SUPERADMIN.value,
        UserRole.PANADERO.value,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para confirmar pedidos.",
        )

    try:
        receipt = ReceiptService.confirm_order(db, order_id)
        return {
            "idPedido": receipt.pedido_idPedido,
            "estadoPedido": "En preparación",
            "reciboGenerado": True,
        }
    except ReceiptOrderNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except ReceiptConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
