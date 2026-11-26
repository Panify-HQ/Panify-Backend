from typing import Optional

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.auth import get_current_user, get_optional_user, require_roles  # ajusta
from app.infrastructure.database.session import get_db  # ajusta
from app.schemas.inventario import (
    DescuentoIn,
    ProductoActualizar,
    ProductoCrear,
    ProductoOut,
    a_producto_out,
)
from app.services import inventario_service as svc

router = APIRouter(prefix="/api/v1/inventario", tags=["inventario"])

ROLES_GESTION = ("Administrador", "Panadero")


def es_gestor(usuario) -> bool:
    return usuario is not None and usuario.rol in ROLES_GESTION


@router.post("/productos", status_code=201, response_model=ProductoOut)
def crear_producto(
    datos: ProductoCrear,
    db: Session = Depends(get_db),
    _=Depends(require_roles(*ROLES_GESTION)),
):
    producto = svc.crear_producto(
        db, datos.nombre, datos.precio, datos.stockInicial, datos.categoria
    )
    return a_producto_out(producto)


@router.patch("/productos/{id_producto}", response_model=ProductoOut)
def actualizar_producto(
    id_producto: int,
    datos: ProductoActualizar,
    db: Session = Depends(get_db),
    _=Depends(require_roles(*ROLES_GESTION)),
):
    producto = svc.actualizar_producto(db, id_producto, datos.precio, datos.stock)
    return a_producto_out(producto)


@router.get("/productos", response_model=list[ProductoOut])
def listar_productos(
    categoria: Optional[str] = Query(default=None, max_length=250),
    db: Session = Depends(get_db),
    usuario=Depends(get_optional_user),
):
    productos = svc.listar_productos(db, categoria, ver_todos=es_gestor(usuario))
    return [a_producto_out(p) for p in productos]


@router.get("/productos/{id_producto}", response_model=ProductoOut)
def obtener_producto(
    id_producto: int,
    db: Session = Depends(get_db),
    usuario=Depends(get_optional_user),
):
    producto = svc.obtener_producto(db, id_producto, ver_todos=es_gestor(usuario))
    return a_producto_out(producto)


@router.get("/productos/{id_producto}/disponibilidad")
def validar_disponibilidad(
    id_producto: int,
    cantidad: int = Query(gt=0),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return {"disponible": svc.validar_disponibilidad(db, id_producto, cantidad)}


@router.post("/movimientos/descuento")
def descontar_stock(
    datos: DescuentoIn,
    db: Session = Depends(get_db),
    _=Depends(require_roles("Sistema")),
):
    items = [(i.id, i.cantidad) for i in datos.productos]
    svc.descontar_stock(db, datos.idPedido, items)
    return {"idPedido": datos.idPedido, "estado": "Descontado"}


@router.get("/alertas", response_model=list[ProductoOut])
def alertas_stock(
    umbral: Optional[int] = Query(default=None, ge=0),
    db: Session = Depends(get_db),
    _=Depends(require_roles(*ROLES_GESTION)),
):
    return [a_producto_out(p) for p in svc.alertas_stock(db, umbral)]


@router.delete("/productos/{id_producto}", status_code=204)
def inactivar_producto(
    id_producto: int,
    db: Session = Depends(get_db),
    _=Depends(require_roles("Administrador")),
):
    svc.inactivar_producto(db, id_producto)
    return Response(status_code=204)