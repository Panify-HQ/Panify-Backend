from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.infrastructure.database.session import get_db
from app.models.usuario import Usuario
from app.schemas.receipt import ReceiptCreationResponse
from app.schemas.user import UserRole
from app.services.receipt_service import (
    OrderNotFoundError,
    ReceiptConflictError,
    ReceiptService,
)

router = APIRouter(prefix="/orders", tags=["Orders"])


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
    except OrderNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except ReceiptConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
