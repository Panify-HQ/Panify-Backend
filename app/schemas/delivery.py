from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.schemas.order import OrderState


class DeliveryQueueItem(BaseModel):
    idPedido: int
    estadoPedido: OrderState
    fechaHoraCreacion: datetime
    direccion: str
    tiempoEsperaMinutos: int


class DeliveryQueueResponse(BaseModel):
    total: int
    items: list[DeliveryQueueItem]


class DeliveryProductItem(BaseModel):
    nombreProducto: str
    cantidad: int
    precioFijo: Decimal
    subtotal: Decimal


class DeliveryCustomerResponse(BaseModel):
    idPedido: int
    nombreCliente: str
    telefonoCelular: str
    direccion: str
    productos: list[DeliveryProductItem]
    totalPedido: Decimal


class DeliveryHistoryItem(BaseModel):
    idPedido: int
    estadoPedido: OrderState
    fechaHoraCreacion: datetime
    direccion: str


class DeliveryHistoryResponse(BaseModel):
    total: int
    pagina: int
    tamanoPagina: int
    items: list[DeliveryHistoryItem]


class DeliveryStatusUpdate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"examples": [{"estadoPedido": "Entregado"}]}
    )

    estadoPedido: OrderState


class DeliveryStatusResponse(BaseModel):
    idPedido: int
    estadoPedido: OrderState