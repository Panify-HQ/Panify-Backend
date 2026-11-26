from typing import Optional

from pydantic import BaseModel, Field

from app.infrastructure.database.models import Productos  # ajusta
from app.services.inventario_service import calcular_estado_stock, inventario_de, stock_de


class ProductoCrear(BaseModel):
    nombre: str = Field(min_length=1, max_length=250)
    precio: float = Field(gt=0)
    stockInicial: int = Field(ge=0)
    categoria: str = "General"


class ProductoActualizar(BaseModel):
    precio: Optional[float] = Field(default=None, gt=0)
    stock: Optional[int] = Field(default=None, ge=0)


class ProductoOut(BaseModel):
    id: int
    nombre: Optional[str]
    precio: Optional[float]
    categoria: str
    stock: int
    stockMinimo: int
    estadoStock: str
    estado: Optional[str]

    model_config = {"from_attributes": True}


class ItemDescuento(BaseModel):
    id: int
    cantidad: int = Field(gt=0)


class DescuentoIn(BaseModel):
    idPedido: int
    productos: list[ItemDescuento] = Field(min_length=1)


def a_producto_out(p: Productos) -> ProductoOut:
    inv = inventario_de(p)
    stock = stock_de(p)
    minimo = inv.stockMinimo if inv else 0
    return ProductoOut(
        id=p.idProducto,
        nombre=p.nombre,
        precio=p.precio,
        categoria=p.descripcion or "General",
        stock=stock,
        stockMinimo=minimo,
        estadoStock=calcular_estado_stock(stock, minimo),
        estado=p.estado,
    )