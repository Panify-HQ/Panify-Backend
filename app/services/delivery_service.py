from datetime import date, datetime, time, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.cliente import Cliente
from app.models.detalle_pedido import DetallePedido
from app.models.pedidos import Pedido
from app.models.usuario import Usuario
from app.schemas.order import OrderState
from app.schemas.user import UserRole
from app.services.order_service import OrderService


class DeliveryServiceError(Exception):
    pass


class DeliveryNotFoundError(DeliveryServiceError):
    pass


class DeliveryForbiddenError(DeliveryServiceError):
    pass


class DeliveryInvalidError(DeliveryServiceError):
    pass


class DeliveryConflictError(DeliveryServiceError):
    pass


class DeliveryService:
    @staticmethod
    def _now() -> datetime:
        return datetime.now()

    @staticmethod
    def _wait_minutes(created_at: datetime, now: datetime) -> int:
        seconds = (now - created_at).total_seconds()
        return max(int(seconds // 60), 0)

    @staticmethod
    def get_priority_queue(db: Session) -> dict:
        now = DeliveryService._now()
        orders = db.scalars(
            select(Pedido)
            .where(
                Pedido.estadoPedido.in_(
                    [
                        OrderState.PENDIENTE.value,
                        OrderState.EN_PREPARACION.value,
                        OrderState.LISTO.value,
                        OrderState.EN_CAMINO.value,
                    ]
                )
            )
            .options(selectinload(Pedido.cliente))
            .order_by(Pedido.fechaHoraCreacion.asc(), Pedido.idPedido.asc())
        ).all()

        items = [
            {
                "idPedido": order.idPedido,
                "estadoPedido": order.estadoPedido,
                "fechaHoraCreacion": order.fechaHoraCreacion,
                "direccion": order.cliente.direccion,
                "tiempoEsperaMinutos": DeliveryService._wait_minutes(
                    order.fechaHoraCreacion, now
                ),
            }
            for order in orders
        ]

        return {"total": len(items), "items": items}

    @staticmethod
    def get_customer_info(db: Session, order_id: int, current_user: Usuario) -> dict:
        order = db.scalar(
            select(Pedido)
            .where(Pedido.idPedido == order_id)
            .options(
                selectinload(Pedido.cliente).selectinload(Cliente.usuarios),
                selectinload(Pedido.detalles_pedido).selectinload(
                    DetallePedido.producto
                ),
            )
        )
        if order is None:
            raise DeliveryNotFoundError()

        if current_user.rol.nombre == UserRole.DOMICILIARIO.value:
            own_id = current_user.domiciliario_idDomiciliario
            assigned_id = order.domiciliario_idDomiciliario
            if own_id is None or (assigned_id is not None and assigned_id != own_id):
                raise DeliveryForbiddenError()

        customer = order.cliente
        customer_user = customer.usuarios[0] if customer and customer.usuarios else None
        if customer_user is None:
            raise DeliveryNotFoundError()

        products = [
            {
                "nombreProducto": line.producto.nombre or "",
                "cantidad": line.cantidad,
                "precioFijo": line.precioFijo,
                "subtotal": line.precioFijo * line.cantidad,
            }
            for line in order.detalles_pedido
        ]
        total = sum((item["subtotal"] for item in products), Decimal("0.00"))

        return {
            "idPedido": order.idPedido,
            "nombreCliente": f"{customer_user.nombre} {customer_user.apellido}",
            "telefonoCelular": customer_user.telefono,
            "direccion": customer.direccion,
            "productos": products,
            "totalPedido": total,
        }

    @staticmethod
    def filter_history(
        db: Session,
        fecha_inicio: date,
        fecha_fin: date | None,
        page: int,
        page_size: int,
    ) -> dict:
        today = DeliveryService._now().date()
        fecha_fin = fecha_fin or fecha_inicio

        if fecha_inicio > fecha_fin:
            raise DeliveryInvalidError()
        if fecha_inicio > today or fecha_fin > today:
            raise DeliveryInvalidError()

        start = datetime.combine(fecha_inicio, time.min)
        end = datetime.combine(fecha_fin + timedelta(days=1), time.min)
        query = select(Pedido).where(
            Pedido.fechaHoraCreacion >= start,
            Pedido.fechaHoraCreacion < end,
        )

        total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
        orders = db.scalars(
            query.options(selectinload(Pedido.cliente))
            .order_by(Pedido.fechaHoraCreacion.desc(), Pedido.idPedido.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()

        return {
            "total": total,
            "pagina": page,
            "tamanoPagina": page_size,
            "items": [
                {
                    "idPedido": order.idPedido,
                    "estadoPedido": order.estadoPedido,
                    "fechaHoraCreacion": order.fechaHoraCreacion,
                    "direccion": order.cliente.direccion,
                }
                for order in orders
            ],
        }

    @staticmethod
    def update_order_status(
        db: Session,
        order_id: int,
        new_state: OrderState,
        current_user: Usuario,
    ) -> dict:
        next_state = {
            OrderState.PENDIENTE.value: OrderState.EN_PREPARACION.value,
            OrderState.EN_PREPARACION.value: OrderState.LISTO.value,
            OrderState.LISTO.value: OrderState.EN_CAMINO.value,
            OrderState.EN_CAMINO.value: OrderState.ENTREGADO.value,
        }

        try:
            order = db.scalar(
                select(Pedido)
                .where(Pedido.idPedido == order_id)
                .options(selectinload(Pedido.detalles_pedido))
                .with_for_update()
            )
            if order is None:
                raise DeliveryNotFoundError()

            is_courier = current_user.rol.nombre == UserRole.DOMICILIARIO.value
            own_id = current_user.domiciliario_idDomiciliario
            assigned_id = order.domiciliario_idDomiciliario

            if is_courier and (
                own_id is None or (assigned_id is not None and assigned_id != own_id)
            ):
                raise DeliveryForbiddenError()

            current_state = order.estadoPedido
            if new_state.value == OrderState.CANCELADO.value:
                if current_state in (
                    OrderState.ENTREGADO.value,
                    OrderState.CANCELADO.value,
                ):
                    raise DeliveryConflictError()
                OrderService._restore_stock(db, order)
            elif next_state.get(current_state) != new_state.value:
                raise DeliveryConflictError()

            if (
                new_state.value == OrderState.EN_CAMINO.value
                and is_courier
                and assigned_id is None
            ):
                order.domiciliario_idDomiciliario = own_id

            order.estadoPedido = new_state.value
            db.commit()
            return {"idPedido": order.idPedido, "estadoPedido": order.estadoPedido}
        except Exception:
            db.rollback()
            raise