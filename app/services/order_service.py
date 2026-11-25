from collections import defaultdict
from datetime import date, datetime, time, timedelta
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.cliente import Cliente
from app.models.detalle_pedido import DetallePedido
from app.models.domiciliario import Domiciliario
from app.models.inventarios import Inventarios
from app.models.pedidos import Pedido
from app.models.productos import Productos
from app.models.rutasParada import RutaParada
from app.models.usuario import Usuario
from app.schemas.order import OrderCreate, OrderState, OrderStatusUpdate
from app.schemas.user import UserRole

ACTIVE_STATES = (
    OrderState.PENDIENTE.value,
    OrderState.EN_PREPARACION.value,
    OrderState.LISTO.value,
    OrderState.EN_CAMINO.value,
)
FINAL_STATES = (OrderState.ENTREGADO.value, OrderState.CANCELADO.value)
VALID_TRANSITIONS = {
    OrderState.PENDIENTE.value: OrderState.EN_PREPARACION.value,
    OrderState.EN_PREPARACION.value: OrderState.LISTO.value,
    OrderState.LISTO.value: OrderState.EN_CAMINO.value,
    OrderState.EN_CAMINO.value: OrderState.ENTREGADO.value,
}


class OrderServiceError(Exception):
    pass


class OrderNotFoundError(OrderServiceError):
    pass


class OrderForbiddenError(OrderServiceError):
    pass


class OrderInvalidError(OrderServiceError):
    pass


class OrderConflictError(OrderServiceError):
    pass


class OrderService:
    @staticmethod
    def _now() -> datetime:
        return datetime.now()

    @staticmethod
    def _server_datetime(value: datetime) -> datetime:
        # La base usa DateTime sin zona; se normaliza al huso local del servidor.
        if value.tzinfo is not None and value.utcoffset() is not None:
            return value.astimezone().replace(tzinfo=None)
        return value

    @staticmethod
    def _total(order: Pedido) -> Decimal:
        return sum(
            (
                Decimal(line.cantidad) * line.precioFijo
                for line in order.detalles_pedido
            ),
            Decimal("0.00"),
        )

    @staticmethod
    def _product_lines(order: Pedido) -> list[dict]:
        return [
            {
                "idProducto": line.producto_idProducto,
                "nombreProducto": line.producto.nombre or "",
                "cantidad": line.cantidad,
                "precioFijo": line.precioFijo,
                "subtotal": line.precioFijo * line.cantidad,
            }
            for line in order.detalles_pedido
        ]

    @staticmethod
    def _order_options():
        return (
            selectinload(Pedido.cliente).selectinload(Cliente.usuarios),
            selectinload(Pedido.domiciliario).selectinload(Domiciliario.usuarios),
            selectinload(Pedido.detalles_pedido).selectinload(DetallePedido.producto),
            selectinload(Pedido.recibo),
            selectinload(Pedido.paradas_ruta).selectinload(RutaParada.ruta_entrega),
        )

    @staticmethod
    def _role(user: Usuario) -> str:
        return user.rol.nombre

    @staticmethod
    def _apply_list_scope(query, current_user: Usuario):
        role = OrderService._role(current_user)
        if role == UserRole.CLIENTE.value:
            if current_user.cliente_idCliente is None:
                raise OrderForbiddenError(
                    "La cuenta no tiene un perfil de cliente asociado."
                )
            return query.where(
                Pedido.cliente_idCliente == current_user.cliente_idCliente
            )
        if role == UserRole.DOMICILIARIO.value:
            if current_user.domiciliario_idDomiciliario is None:
                raise OrderForbiddenError(
                    "La cuenta no tiene un perfil de domiciliario asociado."
                )
            return query.where(
                Pedido.domiciliario_idDomiciliario
                == current_user.domiciliario_idDomiciliario
            )
        if role in (
            UserRole.PANADERO.value,
            UserRole.ADMINISTRADOR.value,
            UserRole.SUPERADMIN.value,
        ):
            return query
        raise OrderForbiddenError("No tienes permisos para consultar pedidos.")

    @staticmethod
    def _assert_detail_access(current_user: Usuario, order: Pedido) -> None:
        role = OrderService._role(current_user)
        if role == UserRole.CLIENTE.value:
            if current_user.cliente_idCliente != order.cliente_idCliente:
                raise OrderForbiddenError("El pedido no pertenece a este cliente.")
            return
        if role == UserRole.DOMICILIARIO.value:
            if (
                current_user.domiciliario_idDomiciliario is None
                or current_user.domiciliario_idDomiciliario
                != order.domiciliario_idDomiciliario
            ):
                raise OrderForbiddenError(
                    "El pedido no está asignado a este domiciliario."
                )
            return
        if role in (
            UserRole.PANADERO.value,
            UserRole.ADMINISTRADOR.value,
        ):
            return
        raise OrderForbiddenError("No tienes permisos para consultar este pedido.")

    @staticmethod
    def _load_order(db: Session, order_id: int, *, lock: bool = False) -> Pedido:
        statement = select(Pedido).where(Pedido.idPedido == order_id)
        if lock:
            statement = statement.with_for_update()
        order = db.scalar(statement.options(*OrderService._order_options()))
        if order is None:
            raise OrderNotFoundError("Pedido no encontrado.")
        return order

    @staticmethod
    def create_order(
        db: Session,
        data: OrderCreate,
        current_user: Usuario,
    ) -> dict:
        if (
            OrderService._role(current_user) != UserRole.CLIENTE.value
            or current_user.cliente_idCliente is None
            or data.cliente_idCliente != current_user.cliente_idCliente
        ):
            raise OrderForbiddenError(
                "Solo puedes crear pedidos para tu perfil de cliente."
            )
        if not data.listaProductos:
            raise OrderInvalidError("El pedido debe contener al menos un producto.")
        if any(line.cantidad <= 0 for line in data.listaProductos):
            raise OrderInvalidError(
                "La cantidad de cada producto debe ser mayor que cero."
            )

        now = OrderService._now()
        estimated_delivery = OrderService._server_datetime(
            data.fechaHoraEntregaEstimada
        )
        if estimated_delivery <= now:
            raise OrderInvalidError(
                "La entrega estimada debe ser posterior a la fecha y hora actuales."
            )
        if estimated_delivery.date() == now.date() and estimated_delivery.time() > time(
            18, 0
        ):
            raise OrderInvalidError(
                "Para entregas después de las 18:00, programa el pedido desde el día siguiente."
            )

        quantities: dict[int, int] = {}
        product_order: list[int] = []
        for requested_line in data.listaProductos:
            product_id = requested_line.idProducto
            if product_id not in quantities:
                quantities[product_id] = 0
                product_order.append(product_id)
            quantities[product_id] += requested_line.cantidad
        product_ids = sorted(quantities)

        try:
            customer = db.get(Cliente, current_user.cliente_idCliente)
            if customer is None:
                raise OrderForbiddenError(
                    "No se encontró el perfil de cliente autenticado."
                )

            products = db.scalars(
                select(Productos)
                .where(Productos.idProducto.in_(product_ids))
                .order_by(Productos.idProducto)
                .with_for_update()
            ).all()
            products_by_id = {product.idProducto: product for product in products}
            missing_products = [
                product_id
                for product_id in product_order
                if product_id not in products_by_id
            ]
            if missing_products:
                raise OrderInvalidError(f"No existe el producto {missing_products[0]}.")

            inventory_rows = db.scalars(
                select(Inventarios)
                .where(Inventarios.producto_idProducto.in_(product_ids))
                .order_by(
                    Inventarios.producto_idProducto,
                    Inventarios.idInventario,
                )
                .with_for_update()
            ).all()
            inventory_by_product: dict[int, list[Inventarios]] = defaultdict(list)
            for inventory in inventory_rows:
                inventory_by_product[inventory.producto_idProducto].append(inventory)

            prices: dict[int, Decimal] = {}
            for product_id in product_order:
                product = products_by_id[product_id]
                if product.estado != "ACTIVO":
                    raise OrderInvalidError(
                        f"El producto {product.nombre or product_id} no está activo."
                    )
                if product.precio is None:
                    raise OrderConflictError(
                        f"El producto {product.nombre or product_id} no tiene precio configurado."
                    )
                price = Decimal(str(product.precio)).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                if price <= 0:
                    raise OrderConflictError(
                        f"El producto {product.nombre or product_id} tiene un precio inválido."
                    )
                prices[product_id] = price

                available = sum(
                    row.stockActual for row in inventory_by_product.get(product_id, [])
                )
                if quantities[product_id] > available:
                    raise OrderConflictError(
                        f"Stock insuficiente para {product.nombre or product_id}: "
                        f"disponibles {available}, solicitados {quantities[product_id]}."
                    )

            for product_id in product_order:
                remaining = quantities[product_id]
                for inventory in inventory_by_product[product_id]:
                    taken = min(inventory.stockActual, remaining)
                    inventory.stockActual -= taken
                    remaining -= taken
                    if remaining == 0:
                        break

            order = Pedido(
                fechaHoraCreacion=now,
                fechaHoraEntregaEstimada=estimated_delivery,
                estadoPedido=OrderState.PENDIENTE.value,
                cliente_idCliente=current_user.cliente_idCliente,
            )
            db.add(order)
            db.flush()

            for product_id in product_order:
                db.add(
                    DetallePedido(
                        pedido_idPedido=order.idPedido,
                        producto_idProducto=product_id,
                        cantidad=quantities[product_id],
                        precioFijo=prices[product_id],
                    )
                )
            db.flush()

            lines = [
                {
                    "idProducto": product_id,
                    "nombreProducto": products_by_id[product_id].nombre or "",
                    "cantidad": quantities[product_id],
                    "precioFijo": prices[product_id],
                    "subtotal": prices[product_id] * quantities[product_id],
                }
                for product_id in product_order
            ]
            total = sum((line["subtotal"] for line in lines), Decimal("0.00"))
            response = {
                "idPedido": order.idPedido,
                "estadoPedido": order.estadoPedido,
                "fechaHoraCreacion": order.fechaHoraCreacion,
                "fechaHoraEntregaEstimada": order.fechaHoraEntregaEstimada,
                "detalles_pedido": lines,
                "total": total,
            }
            db.commit()
            return response
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def _list_response(
        orders: list[Pedido],
        page: int,
        page_size: int,
        total: int,
    ) -> dict:
        return {
            "items": [
                {
                    "idPedido": order.idPedido,
                    "fechaHoraCreacion": order.fechaHoraCreacion,
                    "fechaHoraEntregaEstimada": order.fechaHoraEntregaEstimada,
                    "estadoPedido": order.estadoPedido,
                    "grupoEstado": (
                        "Historial" if order.estadoPedido in FINAL_STATES else "Activo"
                    ),
                    "total": OrderService._total(order),
                }
                for order in orders
            ],
            "pagina": page,
            "tamanoPagina": page_size,
            "total": total,
        }

    @staticmethod
    def list_orders(
        db: Session,
        current_user: Usuario,
        estado: OrderState | None,
        text_filter: str | None,
        page: int,
        page_size: int,
    ) -> dict:
        query = OrderService._apply_list_scope(select(Pedido), current_user)
        if estado is not None:
            query = query.where(Pedido.estadoPedido == estado.value)
        if text_filter:
            term = f"%{text_filter.strip()}%"
            query = query.where(
                or_(
                    cast(Pedido.idPedido, String).ilike(term),
                    Pedido.detalles_pedido.any(
                        DetallePedido.producto.has(Productos.nombre.ilike(term))
                    ),
                )
            )

        total = (
            db.scalar(select(func.count()).select_from(query.order_by(None).subquery()))
            or 0
        )
        orders = db.scalars(
            query.options(
                selectinload(Pedido.detalles_pedido).selectinload(
                    DetallePedido.producto
                )
            )
            .order_by(Pedido.fechaHoraCreacion.desc(), Pedido.idPedido.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return OrderService._list_response(orders, page, page_size, total)

    @staticmethod
    def get_order_detail(
        db: Session,
        order_id: int,
        current_user: Usuario,
    ) -> dict:
        order = OrderService._load_order(db, order_id)
        OrderService._assert_detail_access(current_user, order)
        customer_user = next(
            (
                user
                for user in order.cliente.usuarios
                if user.rol.nombre == UserRole.CLIENTE.value
            ),
            None,
        )
        courier_user = (
            order.domiciliario.usuarios[0]
            if order.domiciliario is not None and order.domiciliario.usuarios
            else None
        )
        return {
            "idPedido": order.idPedido,
            "fechaHoraCreacion": order.fechaHoraCreacion,
            "fechaHoraEntregaEstimada": order.fechaHoraEntregaEstimada,
            "estadoPedido": order.estadoPedido,
            "cliente": {
                "idCliente": order.cliente.idCliente,
                "nombre": customer_user.nombre if customer_user else None,
                "apellido": customer_user.apellido if customer_user else None,
                "direccion": order.cliente.direccion,
            },
            "domiciliario": (
                {
                    "idDomiciliario": order.domiciliario.idDomiciliario,
                    "nombre": courier_user.nombre if courier_user else None,
                    "apellido": courier_user.apellido if courier_user else None,
                }
                if order.domiciliario is not None
                else None
            ),
            "detalles_pedido": OrderService._product_lines(order),
            "recibo": (
                {
                    "idRecibo": order.recibo.idRecibo,
                    "totalPagar": order.recibo.totalPagar,
                    "fechaEmision": order.recibo.fechaEmision,
                }
                if order.recibo is not None
                else None
            ),
            "paradas_ruta": [
                {
                    "idRutasParada": stop.idRutasParada,
                    "idRutasEntrega": stop.rutasEntrega_idRutasEntrega,
                    "ordenEntrega": stop.ordenEntrega,
                    "estadoParada": stop.estadoParada,
                    "urlRutaGoogle": (
                        stop.ruta_entrega.urlRutaGoogle
                        if stop.ruta_entrega is not None
                        else None
                    ),
                }
                for stop in order.paradas_ruta
            ],
            "total": OrderService._total(order),
        }

    @staticmethod
    def _locked_inventory_for_order(
        db: Session,
        order: Pedido,
    ) -> dict[int, list[Inventarios]]:
        product_ids = sorted(
            {line.producto_idProducto for line in order.detalles_pedido}
        )
        if not product_ids:
            raise OrderConflictError(
                "No se puede cancelar un pedido sin detalles de productos."
            )
        rows = db.scalars(
            select(Inventarios)
            .where(Inventarios.producto_idProducto.in_(product_ids))
            .order_by(
                Inventarios.producto_idProducto,
                Inventarios.idInventario,
            )
            .with_for_update()
        ).all()
        inventory_by_product: dict[int, list[Inventarios]] = defaultdict(list)
        for row in rows:
            inventory_by_product[row.producto_idProducto].append(row)
        missing = [
            product_id
            for product_id in product_ids
            if not inventory_by_product[product_id]
        ]
        if missing:
            raise OrderConflictError(
                f"No se puede reponer el stock del producto {missing[0]}: "
                "no existe una fila de inventario."
            )
        return inventory_by_product

    @staticmethod
    def _restore_stock(db: Session, order: Pedido) -> None:
        inventory_by_product = OrderService._locked_inventory_for_order(db, order)
        for line in order.detalles_pedido:
            inventory_by_product[line.producto_idProducto][
                0
            ].stockActual += line.cantidad

    @staticmethod
    def _cancel_locked_order(
        db: Session,
        order: Pedido,
        current_user: Usuario,
    ) -> None:
        role = OrderService._role(current_user)
        if role == UserRole.CLIENTE.value:
            if current_user.cliente_idCliente != order.cliente_idCliente:
                raise OrderForbiddenError("El pedido no pertenece a este cliente.")
            if order.estadoPedido != OrderState.PENDIENTE.value:
                raise OrderConflictError(
                    "El cliente solo puede cancelar pedidos en estado Pendiente."
                )
        elif role == UserRole.ADMINISTRADOR.value:
            if order.estadoPedido in FINAL_STATES:
                raise OrderConflictError(
                    "No se puede cancelar un pedido Entregado o ya Cancelado."
                )
        else:
            raise OrderForbiddenError(
                "Solo el cliente propietario o un Administrador puede cancelar pedidos."
            )

        OrderService._restore_stock(db, order)
        order.estadoPedido = OrderState.CANCELADO.value

    @staticmethod
    def cancel_order(
        db: Session,
        order_id: int,
        current_user: Usuario,
    ) -> dict:
        if OrderService._role(current_user) not in (
            UserRole.CLIENTE.value,
            UserRole.ADMINISTRADOR.value,
        ):
            raise OrderForbiddenError(
                "Solo un Cliente o Administrador puede cancelar pedidos."
            )
        try:
            order = OrderService._load_order(db, order_id, lock=True)
            OrderService._cancel_locked_order(db, order, current_user)
            db.commit()
            return {
                "idPedido": order.idPedido,
                "estadoPedido": order.estadoPedido,
                "domiciliario_idDomiciliario": order.domiciliario_idDomiciliario,
            }
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def update_status(
        db: Session,
        order_id: int,
        data: OrderStatusUpdate,
        current_user: Usuario,
    ) -> dict:
        role = OrderService._role(current_user)
        if role not in (
            UserRole.PANADERO.value,
            UserRole.DOMICILIARIO.value,
            UserRole.ADMINISTRADOR.value,
        ):
            raise OrderForbiddenError(
                "No tienes permisos para cambiar el estado del pedido."
            )

        try:
            order = OrderService._load_order(db, order_id, lock=True)
            now = OrderService._server_datetime(OrderService._now())
            created_at = OrderService._server_datetime(order.fechaHoraCreacion)
            if now < created_at:
                raise OrderConflictError(
                    "La hora de la transición no puede ser anterior a la creación del pedido."
                )

            if data.nuevoEstado == OrderState.CANCELADO:
                if role != UserRole.ADMINISTRADOR.value:
                    raise OrderForbiddenError(
                        "Solo un Administrador puede cancelar desde este endpoint."
                    )
                OrderService._cancel_locked_order(db, order, current_user)
            else:
                expected_state = VALID_TRANSITIONS.get(order.estadoPedido)
                if data.nuevoEstado.value != expected_state:
                    raise OrderConflictError(
                        f"Transición inválida desde {order.estadoPedido} a "
                        f"{data.nuevoEstado.value}."
                    )

                if role == UserRole.DOMICILIARIO.value:
                    courier_id = current_user.domiciliario_idDomiciliario
                    if (
                        courier_id is None
                        or order.domiciliario_idDomiciliario != courier_id
                    ):
                        raise OrderForbiddenError(
                            "Solo puedes actualizar pedidos asignados a tu perfil."
                        )

                if data.nuevoEstado == OrderState.EN_CAMINO:
                    requested_courier_id = data.domiciliario_idDomiciliario
                    if role == UserRole.DOMICILIARIO.value:
                        courier_id = current_user.domiciliario_idDomiciliario
                        if requested_courier_id not in (None, courier_id):
                            raise OrderForbiddenError(
                                "No puedes asignar el pedido a otro domiciliario."
                            )
                    elif requested_courier_id is not None:
                        courier = db.get(Domiciliario, requested_courier_id)
                        if courier is None:
                            raise OrderInvalidError(
                                "El domiciliario indicado no existe."
                            )
                        order.domiciliario_idDomiciliario = requested_courier_id
                    if order.domiciliario_idDomiciliario is None:
                        raise OrderInvalidError(
                            "Debes asignar un domiciliario antes de pasar el pedido a En camino."
                        )
                elif data.domiciliario_idDomiciliario is not None:
                    raise OrderInvalidError(
                        "El domiciliario solo se puede asignar al pasar a En camino."
                    )

                order.estadoPedido = data.nuevoEstado.value

            db.commit()
            return {
                "idPedido": order.idPedido,
                "estadoPedido": order.estadoPedido,
                "domiciliario_idDomiciliario": order.domiciliario_idDomiciliario,
            }
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def dispatch_queue(db: Session) -> list[dict]:
        orders = db.scalars(
            select(Pedido)
            .where(Pedido.estadoPedido.in_(ACTIVE_STATES))
            .options(
                selectinload(Pedido.detalles_pedido).selectinload(
                    DetallePedido.producto
                )
            )
            .order_by(Pedido.fechaHoraCreacion.asc(), Pedido.idPedido.asc())
        ).all()
        return OrderService._list_response(
            list(orders), page=1, page_size=len(orders), total=len(orders)
        )["items"]

    @staticmethod
    def history_filter(
        db: Session,
        current_user: Usuario,
        fecha_inicio: date,
        fecha_fin: date,
        page: int,
        page_size: int,
    ) -> dict:
        role = OrderService._role(current_user)
        if role not in (
            UserRole.ADMINISTRADOR.value,
            UserRole.SUPERADMIN.value,
            UserRole.CLIENTE.value,
        ):
            raise OrderForbiddenError(
                "No tienes permisos para consultar el historial filtrado."
            )
        if fecha_inicio > fecha_fin:
            raise OrderInvalidError("fechaInicio no puede ser posterior a fechaFin.")
        today = OrderService._now().date()
        if fecha_inicio > today or fecha_fin > today:
            raise OrderInvalidError(
                "El rango de fechas no puede incluir fechas futuras."
            )

        start_datetime = datetime.combine(fecha_inicio, time.min)
        end_datetime = datetime.combine(fecha_fin + timedelta(days=1), time.min)
        query = select(Pedido).where(
            Pedido.fechaHoraCreacion >= start_datetime,
            Pedido.fechaHoraCreacion < end_datetime,
        )
        if role == UserRole.CLIENTE.value:
            if current_user.cliente_idCliente is None:
                raise OrderForbiddenError(
                    "La cuenta no tiene un perfil de cliente asociado."
                )
            query = query.where(
                Pedido.cliente_idCliente == current_user.cliente_idCliente
            )

        total = (
            db.scalar(select(func.count()).select_from(query.order_by(None).subquery()))
            or 0
        )
        orders = db.scalars(
            query.options(
                selectinload(Pedido.detalles_pedido).selectinload(
                    DetallePedido.producto
                )
            )
            .order_by(Pedido.fechaHoraCreacion.desc(), Pedido.idPedido.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return OrderService._list_response(orders, page, page_size, total)
