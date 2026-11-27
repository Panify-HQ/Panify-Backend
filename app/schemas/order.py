from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class OrderState(str, Enum):
    PENDIENTE = "Pendiente"
    EN_PREPARACION = "En preparación"
    LISTO = "Listo"
    EN_CAMINO = "En camino"
    ENTREGADO = "Entregado"
    CANCELADO = "Cancelado"


class OrderSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class OrderProductCreate(OrderSchema):
    idProducto: int = Field(gt=0)
    cantidad: int


class OrderCreate(OrderSchema):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "listaProductos": [
                        {"idProducto": 1, "cantidad": 2},
                        {"idProducto": 3, "cantidad": 1},
                    ],
                    "fechaHoraEntregaEstimada": "2030-05-21T10:00:00",
                },
                {
                    "cliente_idCliente": 12,
                    "listaProductos": [{"idProducto": 1, "cantidad": 2}],
                    "fechaHoraEntregaEstimada": "2030-05-21T10:00:00",
                },
            ]
        }
    )

    cliente_idCliente: int | None = Field(default=None, gt=0)
    listaProductos: list[OrderProductCreate]
    fechaHoraEntregaEstimada: datetime


class OrderStatusUpdate(OrderSchema):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"nuevoEstado": "En preparación"},
                {"nuevoEstado": "Listo"},
                {
                    "nuevoEstado": "En camino",
                    "domiciliario_idDomiciliario": 7,
                },
                {"nuevoEstado": "Entregado"},
                {"nuevoEstado": "Cancelado"},
            ]
        }
    )

    nuevoEstado: OrderState
    domiciliario_idDomiciliario: int | None = Field(default=None, gt=0)


class OrderProductLine(OrderSchema):
    idProducto: int
    nombreProducto: str
    cantidad: int
    precioFijo: Decimal
    subtotal: Decimal


class OrderCreateResponse(OrderSchema):
    idPedido: int
    estadoPedido: OrderState
    fechaHoraCreacion: datetime
    fechaHoraEntregaEstimada: datetime
    detalles_pedido: list[OrderProductLine]
    total: Decimal


class OrderListItem(OrderSchema):
    idPedido: int
    fechaHoraCreacion: datetime
    fechaHoraEntregaEstimada: datetime
    estadoPedido: OrderState
    grupoEstado: str
    total: Decimal


class OrderListResponse(OrderSchema):
    items: list[OrderListItem]
    pagina: int
    tamanoPagina: int
    total: int


class OrderClientInfo(OrderSchema):
    idCliente: int
    nombre: str | None
    apellido: str | None
    direccion: str


class OrderCourierInfo(OrderSchema):
    idDomiciliario: int
    nombre: str | None
    apellido: str | None


class OrderReceiptInfo(OrderSchema):
    idRecibo: int
    totalPagar: Decimal
    fechaEmision: datetime


class OrderRouteStopInfo(OrderSchema):
    idRutasParada: int
    idRutasEntrega: int
    ordenEntrega: int
    estadoParada: str
    urlRutaGoogle: str | None


class OrderDetailResponse(OrderSchema):
    idPedido: int
    fechaHoraCreacion: datetime
    fechaHoraEntregaEstimada: datetime
    estadoPedido: OrderState
    cliente: OrderClientInfo
    domiciliario: OrderCourierInfo | None
    detalles_pedido: list[OrderProductLine]
    recibo: OrderReceiptInfo | None
    paradas_ruta: list[OrderRouteStopInfo]
    total: Decimal


class OrderStatusResponse(OrderSchema):
    idPedido: int
    estadoPedido: OrderState
    domiciliario_idDomiciliario: int | None
