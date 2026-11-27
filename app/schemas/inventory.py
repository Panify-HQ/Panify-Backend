from typing import Optional

from pydantic import BaseModel, Field

from app.models.productos import Productos  # ajusta
from app.services.inventory import calcular_estado_stock, inventario_de, stock_de


class ProductoCrear(BaseModel):
    nombre: str = Field(min_length=1, max_length=250)
    precio: float = Field(gt=0)
    stockInicial: int = Field(ge=0)
    categoria: str = Field(default="General", min_length=1, max_length=250)
    descripcion: str | None = Field(default=None, max_length=250)


class ProductoActualizar(BaseModel):
    precio: Optional[float] = Field(default=None, gt=0)
    stock: Optional[int] = Field(default=None, ge=0)


class ProductoOut(BaseModel):
    id: int
    nombre: Optional[str]
    precio: Optional[float]
    categoria: str
    descripcion: str | None
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
        categoria=p.categoria or "General",
        descripcion=p.descripcion,
        stock=stock,
        stockMinimo=minimo,
        estadoStock=calcular_estado_stock(stock, minimo),
        estado=p.estado,
    )