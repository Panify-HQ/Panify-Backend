from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class ReceiptOrderSummary(BaseModel):
    idPedido: int
    estadoPedido: str
    fechaHoraCreacion: datetime


class ReceiptListItem(BaseModel):
    idRecibo: int
    fechaEmision: datetime
    totalPagar: Decimal
    pedido: ReceiptOrderSummary
    nombreCliente: str


class ReceiptListResponse(BaseModel):
    items: list[ReceiptListItem]
    pagina: int
    tamanoPagina: int
    total: int


class ReceiptCreationResponse(BaseModel):
    idPedido: int
    estadoPedido: str
    reciboGenerado: bool


class ReceiptClient(BaseModel):
    idCliente: int
    nombre: str
    apellido: str
    correo: str
    telefono: str
    direccion: str


class ReceiptProductLine(BaseModel):
    idProducto: int
    nombreProducto: str
    cantidad: int
    precioUnitario: Decimal
    subtotal: Decimal


class ReceiptOrderDetail(BaseModel):
    idPedido: int
    estadoPedido: str
    fechaHoraCreacion: datetime
    fechaHoraEntregaEstimada: datetime


class ReceiptDetail(BaseModel):
    idRecibo: int
    fechaEmision: datetime
    totalPagar: Decimal
    pedido: ReceiptOrderDetail
    cliente: ReceiptClient
    productos: list[ReceiptProductLine]
