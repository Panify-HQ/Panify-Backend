from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.infrastructure.database.models import DetallePedido, Inventarios, Productos  # ajusta

ESTADO_ACTIVO = "ACTIVO"
ESTADO_INACTIVO = "INACTIVO"
ESTADOS_PEDIDO_ACTIVO = ("Pendiente", "En proceso")  # ajusta a tus estados reales


# ---------- Excepciones de dominio ----------
class InventarioError(Exception):
    status_code = 400

    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)


class DatosInvalidos(InventarioError):
    status_code = 400


class SinInventario(InventarioError):
    status_code = 400


class ProductoNoEncontrado(InventarioError):
    status_code = 404


class NombreDuplicado(InventarioError):
    status_code = 409


class StockInsuficiente(InventarioError):
    status_code = 409


class ProductoEnPedidosActivos(InventarioError):
    status_code = 409


# ---------- Helpers ----------
def calcular_estado_stock(stock: int, stock_minimo: int) -> str:
    if stock == 0:
        return "Agotado"
    if stock <= stock_minimo:
        return "Poco Stock"
    return "Disponible"


def inventario_de(producto: Productos) -> Optional[Inventarios]:
    return producto.inventarios[0] if producto.inventarios else None


def stock_de(producto: Productos) -> int:
    inv = inventario_de(producto)
    return inv.stockActual if inv else 0


def _obtener_o_404(db: Session, id_producto: int) -> Productos:
    producto = db.get(Productos, id_producto)
    if producto is None:
        raise ProductoNoEncontrado("Producto no encontrado")
    return producto


def _hay_pedidos_activos(producto: Productos) -> bool:
    # Supone DetallePedido.pedido -> modelo con campo estado; ajusta si difiere
    return any(
        d.pedido is not None and d.pedido.estado in ESTADOS_PEDIDO_ACTIVO
        for d in producto.detalles_pedido
    )


# ---------- Casos de uso ----------
def crear_producto(
    db: Session, nombre: str, precio: float, stock_inicial: int, categoria: str
) -> Productos:
    existe = db.scalar(select(Productos.idProducto).where(Productos.nombre == nombre))
    if existe is not None:
        raise NombreDuplicado("Nombre duplicado")

    producto = Productos(
        nombre=nombre,
        precio=precio,
        estado=ESTADO_ACTIVO,
        descripcion=categoria,
    )
    producto.inventarios.append(Inventarios(stockActual=stock_inicial, stockMinimo=0))
    db.add(producto)
    db.commit()
    db.refresh(producto)
    return producto


def actualizar_producto(
    db: Session,
    id_producto: int,
    precio: Optional[float] = None,
    stock: Optional[int] = None,
) -> Productos:
    if precio is None and stock is None:
        raise DatosInvalidos("Nada que actualizar")

    producto = _obtener_o_404(db, id_producto)

    if precio is not None:
        producto.precio = precio
    if stock is not None:
        inv = inventario_de(producto)
        if inv is None:
            inv = Inventarios(stockActual=0, stockMinimo=0)
            producto.inventarios.append(inv)
        inv.stockActual = stock

    db.commit()
    db.refresh(producto)
    return producto


def listar_productos(
    db: Session, categoria: Optional[str] = None, ver_todos: bool = False
) -> list[Productos]:
    q = select(Productos).options(selectinload(Productos.inventarios))
    if categoria:
        q = q.where(Productos.descripcion == categoria)
    if not ver_todos:
        q = q.where(Productos.estado == ESTADO_ACTIVO)
    return list(db.scalars(q).all())


def obtener_producto(db: Session, id_producto: int, ver_todos: bool = False) -> Productos:
    producto = _obtener_o_404(db, id_producto)
    if not ver_todos and producto.estado != ESTADO_ACTIVO:
        raise ProductoNoEncontrado("Producto no encontrado")
    return producto


def validar_disponibilidad(db: Session, id_producto: int, cantidad: int) -> bool:
    producto = obtener_producto(db, id_producto, ver_todos=False)
    return cantidad <= stock_de(producto)


def descontar_stock(db: Session, id_pedido: int, items: list[tuple[int, int]]) -> None:
    """Descuento transaccional. Agrupa repetidos y bloquea filas en orden de id."""
    if not items:
        raise DatosInvalidos("Sin productos para descontar")

    acumulado: dict[int, int] = {}
    for id_producto, cantidad in items:
        acumulado[id_producto] = acumulado.get(id_producto, 0) + cantidad

    try:
        for id_producto in sorted(acumulado):
            inv = db.scalar(
                select(Inventarios)
                .where(Inventarios.producto_idProducto == id_producto)
                .with_for_update()
            )
            if inv is None:
                raise SinInventario(f"Producto {id_producto} sin inventario")
            if inv.stockActual < acumulado[id_producto]:
                raise StockInsuficiente(f"Stock insuficiente para producto {id_producto}")
            inv.stockActual -= acumulado[id_producto]
        db.commit()
    except Exception:
        db.rollback()
        raise


def alertas_stock(db: Session, umbral: Optional[int] = None) -> list[Productos]:
    productos = listar_productos(db, ver_todos=False)
    resultado = []
    for p in productos:
        inv = inventario_de(p)
        limite = umbral if umbral is not None else (inv.stockMinimo if inv else 0)
        if stock_de(p) <= limite:
            resultado.append(p)
    return resultado


def inactivar_producto(db: Session, id_producto: int) -> None:
    producto = _obtener_o_404(db, id_producto)
    if _hay_pedidos_activos(producto):
        raise ProductoEnPedidosActivos("Producto en pedidos activos")
    producto.estado = ESTADO_INACTIVO
    db.commit()