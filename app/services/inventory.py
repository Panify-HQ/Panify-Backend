from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.inventarios import Inventarios
from app.models.productos import Productos


ESTADO_ACTIVO = "ACTIVO"
ESTADO_INACTIVO = "INACTIVO"
ESTADOS_PEDIDO_ACTIVO = ("Pendiente", "En proceso")


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


def calcular_estado_stock(stock: int, stock_minimo: int) -> str:
    if stock == 0:
        return "Agotado"
    if stock <= stock_minimo:
        return "Poco Stock"
    return "Disponible"


def inventario_de(producto: Productos) -> Inventarios | None:
    return producto.inventarios[0] if producto.inventarios else None


def stock_de(producto: Productos) -> int:
    inventario = inventario_de(producto)
    return inventario.stockActual if inventario is not None else 0


def _obtener_o_404(db: Session, id_producto: int) -> Productos:
    producto = db.get(Productos, id_producto)
    if producto is None:
        raise ProductoNoEncontrado("Producto no encontrado")
    return producto


def _hay_pedidos_activos(producto: Productos) -> bool:
    return any(
        detalle.pedido is not None
        and detalle.pedido.estado in ESTADOS_PEDIDO_ACTIVO
        for detalle in producto.detalles_pedido
    )


def crear_producto(
    db: Session,
    nombre: str,
    precio: float,
    stock_inicial: int,
    categoria: str,
    descripcion: str | None = None,
) -> Productos:
    nombre_existente = db.scalar(
        select(Productos.idProducto).where(Productos.nombre == nombre)
    )
    if nombre_existente is not None:
        raise NombreDuplicado("Nombre duplicado")

    producto = Productos(
        nombre=nombre,
        precio=precio,
        estado=ESTADO_ACTIVO,
        categoria=categoria,
        descripcion=descripcion,
    )
    producto.inventarios.append(
        Inventarios(stockActual=stock_inicial, stockMinimo=0)
    )

    db.add(producto)
    db.commit()
    db.refresh(producto)
    return producto


def actualizar_producto(
    db: Session,
    id_producto: int,
    precio: float | None = None,
    stock: int | None = None,
    nombre: str | None = None,
    categoria: str | None = None,
    stock_minimo: int | None = None,
) -> Productos:
    cambios = (precio, stock, nombre, categoria, stock_minimo)
    if all(valor is None for valor in cambios):
        raise DatosInvalidos("Nada que actualizar")

    producto = _obtener_o_404(db, id_producto)

    if nombre is not None:
        nombre_existente = db.scalar(
            select(Productos.idProducto).where(
                Productos.nombre == nombre,
                Productos.idProducto != id_producto,
            )
        )
        if nombre_existente is not None:
            raise NombreDuplicado("Nombre duplicado")
        producto.nombre = nombre

    if precio is not None:
        producto.precio = precio
    if categoria is not None:
        producto.categoria = categoria

    if stock is not None or stock_minimo is not None:
        inventario = inventario_de(producto)
        if inventario is None:
            inventario = Inventarios(stockActual=0, stockMinimo=0)
            producto.inventarios.append(inventario)

        if stock is not None:
            inventario.stockActual = stock
        if stock_minimo is not None:
            inventario.stockMinimo = stock_minimo

    db.commit()
    db.refresh(producto)
    return producto


def listar_productos(
    db: Session,
    categoria: str | None = None,
    ver_todos: bool = False,
    buscar: str | None = None,
) -> list[Productos]:
    consulta = select(Productos).options(selectinload(Productos.inventarios))

    if categoria:
        consulta = consulta.where(Productos.categoria == categoria)

    termino = buscar.strip() if buscar else ""
    if termino:
        consulta = consulta.where(
            func.lower(Productos.nombre).contains(termino.lower(), autoescape=True)
        )

    if not ver_todos:
        consulta = consulta.where(Productos.estado == ESTADO_ACTIVO)

    return list(db.scalars(consulta).all())


def obtener_producto(
    db: Session, id_producto: int, ver_todos: bool = False
) -> Productos:
    producto = _obtener_o_404(db, id_producto)
    if not ver_todos and producto.estado != ESTADO_ACTIVO:
        raise ProductoNoEncontrado("Producto no encontrado")
    return producto


def validar_disponibilidad(db: Session, id_producto: int, cantidad: int) -> bool:
    producto = obtener_producto(db, id_producto)
    return cantidad <= stock_de(producto)


def descontar_stock(
    db: Session, id_pedido: int, items: list[tuple[int, int]]
) -> None:
    if not items:
        raise DatosInvalidos("Sin productos para descontar")

    cantidades_por_producto: dict[int, int] = {}
    for id_producto, cantidad in items:
        cantidades_por_producto[id_producto] = (
            cantidades_por_producto.get(id_producto, 0) + cantidad
        )

    try:
        for id_producto in sorted(cantidades_por_producto):
            inventario = db.scalar(
                select(Inventarios)
                .where(Inventarios.producto_idProducto == id_producto)
                .with_for_update()
            )
            if inventario is None:
                raise SinInventario(f"Producto {id_producto} sin inventario")

            cantidad = cantidades_por_producto[id_producto]
            if inventario.stockActual < cantidad:
                raise StockInsuficiente(
                    f"Stock insuficiente para producto {id_producto}"
                )

            inventario.stockActual -= cantidad

        db.commit()
    except Exception:
        db.rollback()
        raise


def alertas_stock(db: Session, umbral: int | None = None) -> list[Productos]:
    productos = listar_productos(db)
    resultado = []

    for producto in productos:
        inventario = inventario_de(producto)
        minimo = inventario.stockMinimo if inventario is not None else 0
        limite = umbral if umbral is not None else minimo
        if stock_de(producto) <= limite:
            resultado.append(producto)

    return resultado


def inactivar_producto(db: Session, id_producto: int) -> None:
    producto = _obtener_o_404(db, id_producto)
    if producto.estado != ESTADO_ACTIVO:
        raise DatosInvalidos("El producto debe estar activo para inactivarlo")
    if _hay_pedidos_activos(producto):
        raise ProductoEnPedidosActivos("Producto en pedidos activos")

    producto.estado = ESTADO_INACTIVO
    db.commit()