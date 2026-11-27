from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.routing import APIRoute
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.api.dependencies import bearer_scheme, get_current_user
from app.infrastructure.database.session import get_db
from app.models.usuario import Usuario
from app.schemas.inventory import (
    DescuentoIn,
    ProductoActualizar,
    ProductoCrear,
    ProductoOut,
    a_producto_out,
)
from app.services import inventory as svc


class RutaInventario(APIRoute):
    def get_route_handler(self):
        manejar_solicitud = super().get_route_handler()

        async def manejar_error_inventario(request: Request) -> Response:
            try:
                return await manejar_solicitud(request)
            except svc.InventarioError as error:
                raise HTTPException(
                    status_code=error.status_code,
                    detail=error.detail,
                ) from error

        return manejar_error_inventario


router = APIRouter(
   prefix="/inventory",
    tags=["inventory"],
    route_class=RutaInventario,
)

ROLES_GESTION = ("Administrador", "Panadero")


def get_optional_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Usuario | None:
    if "Authorization" not in request.headers:
        return None

    return get_current_user(credentials=credentials, db=db)


def require_roles(*roles_permitidos: str):
    def verificar_rol(
        usuario: Usuario = Depends(get_current_user),
    ) -> Usuario:
        if usuario.rol is None or usuario.rol.nombre not in roles_permitidos:
            raise HTTPException(
                status_code=403,
                detail="No tienes permiso para esta operación.",
            )

        return usuario

    return verificar_rol


def es_gestor(usuario: Usuario | None) -> bool:
    return (
        usuario is not None
        and usuario.rol is not None
        and usuario.rol.nombre in ROLES_GESTION
    )


@router.post("/products", status_code=201, response_model=ProductoOut,  summary="Create Product")
def crear_producto(
    datos: ProductoCrear,
    db: Session = Depends(get_db),
    _=Depends(require_roles(*ROLES_GESTION)),
):
    producto = svc.crear_producto(
        db,
        nombre=datos.nombre,
        precio=datos.precio,
        stock_inicial=datos.stockInicial,
        categoria=datos.categoria,
        descripcion=datos.descripcion,
    )
    return a_producto_out(producto)


@router.patch("/products/{product_id}", response_model=ProductoOut,  summary="Update Product")
def actualizar_producto(
    id_producto: int,
    datos: ProductoActualizar,
    db: Session = Depends(get_db),
    _=Depends(require_roles(*ROLES_GESTION)),
):
    producto = svc.actualizar_producto(
        db,
        id_producto,
        precio=datos.precio,
        stock=datos.stock,
        nombre=datos.nombre,
        categoria=datos.categoria,
        stock_minimo=datos.stockMinimo,
    )
    return a_producto_out(producto)


@router.get("/products", response_model=list[ProductoOut], summary="List Products")
def listar_productos(
    categoria: str | None = Query(default=None, max_length=250),
    buscar: str | None = Query(default=None, max_length=250),
    db: Session = Depends(get_db),
    usuario: Usuario | None = Depends(get_optional_user),
):
    productos = svc.listar_productos(
        db,
        categoria=categoria,
        ver_todos=es_gestor(usuario),
        buscar=buscar,
    )
    return [a_producto_out(producto) for producto in productos]


@router.get("/productos/{product_id}", response_model=ProductoOut,  summary="Get Product")
def obtener_producto(
    id_producto: int,
    db: Session = Depends(get_db),
    usuario: Usuario | None = Depends(get_optional_user),
):
    producto = svc.obtener_producto(
        db,
        id_producto,
        ver_todos=es_gestor(usuario),
    )
    return a_producto_out(producto)


@router.get("/products/{product_id}/availability", summary="Check Availability")
def validar_disponibilidad(
    id_producto: int,
    cantidad: int = Query(gt=0),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return {"disponible": svc.validar_disponibilidad(db, id_producto, cantidad)}


@router.post("/movements/stock-deduction",  summary="Deduct Stock")
def descontar_stock(
    datos: DescuentoIn,
    db: Session = Depends(get_db),
    _=Depends(require_roles("Sistema")),
):
    items = [(item.id, item.cantidad) for item in datos.productos]
    svc.descontar_stock(db, datos.idPedido, items)
    return {"idPedido": datos.idPedido, "estado": "Descontado"}


@router.get("/alerts", response_model=list[ProductoOut], summary="List Low Stock Alerts")
def alertas_stock(
    umbral: int | None = Query(default=None, ge=0),
    db: Session = Depends(get_db),
    _=Depends(require_roles(*ROLES_GESTION)),
):
    return [a_producto_out(producto) for producto in svc.alertas_stock(db, umbral)]


@router.patch("	/products/{product_id}/deactivate", status_code=204, summary="Deactivate Product")
def inactivar_producto(
    id_producto: int,
    db: Session = Depends(get_db),
    _=Depends(require_roles("Administrador")),
):
    svc.inactivar_producto(db, id_producto)
    return Response(status_code=204)