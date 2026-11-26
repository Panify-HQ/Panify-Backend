from decimal import Decimal

from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models.cliente import Cliente
from app.models.detalle_pedido import DetallePedido
from app.models.pedidos import Pedido
from app.models.recibos import Recibos
from app.models.roles import Rol
from app.models.usuario import Usuario
from app.schemas.user import UserRole


class ReceiptServiceError(Exception):
    pass


class OrderNotFoundError(ReceiptServiceError):
    pass


class ReceiptNotFoundError(ReceiptServiceError):
    pass


class ReceiptConflictError(ReceiptServiceError):
    pass


class ReceiptForbiddenError(ReceiptServiceError):
    pass


class ReceiptService:
    @staticmethod
    def confirm_order(db: Session, order_id: int) -> Recibos:
        order = db.scalar(
            select(Pedido)
            .where(Pedido.idPedido == order_id)
            .with_for_update()
            .options(
                selectinload(Pedido.detalles_pedido),
                selectinload(Pedido.recibo),
            )
        )
        if order is None:
            raise OrderNotFoundError("Pedido no encontrado.")
        if order.estadoPedido != "Pendiente":
            raise ReceiptConflictError(
                "Solo se pueden confirmar pedidos en estado Pendiente."
            )
        if order.recibo is not None:
            raise ReceiptConflictError("El pedido ya tiene un recibo asociado.")

        customer_user = db.scalar(
            select(Usuario)
            .join(Usuario.rol)
            .where(
                Usuario.cliente_idCliente == order.cliente_idCliente,
                Rol.nombre == UserRole.CLIENTE.value,
            )
        )
        if customer_user is None or customer_user.estado != "Activo":
            raise ReceiptConflictError(
                "El pedido debe pertenecer a un cliente con cuenta activa."
            )
        if not order.detalles_pedido:
            raise ReceiptConflictError("El pedido debe contener al menos un producto.")

        total = Decimal("0.00")
        for line in order.detalles_pedido:
            if line.cantidad <= 0 or line.precioFijo <= 0:
                raise ReceiptConflictError(
                    "Cada producto debe tener cantidad y precio congelado mayores que cero."
                )
            total += Decimal(line.cantidad) * line.precioFijo

        receipt = Recibos(
            totalPagar=total,
            pedido_idPedido=order.idPedido,
        )
        order.estadoPedido = "En preparación"
        db.add(receipt)

        try:
            db.commit()
            db.refresh(receipt)
            return receipt
        except IntegrityError as error:
            db.rollback()
            raise ReceiptConflictError(
                "No fue posible emitir el recibo; el pedido ya puede tener uno."
            ) from error
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def list_receipts(
        db: Session,
        current_user: Usuario,
        search: str | None,
        page: int,
        page_size: int,
    ) -> dict:
        query = (
            select(Recibos, Pedido, Usuario)
            .join(Recibos.pedido)
            .join(Cliente, Cliente.idCliente == Pedido.cliente_idCliente)
            .join(Usuario, Usuario.cliente_idCliente == Cliente.idCliente)
            .join(Rol, Rol.idRol == Usuario.Rol_idRol)
            .where(Rol.nombre == UserRole.CLIENTE.value)
        )
        query = ReceiptService._apply_visibility(query, current_user)

        if search:
            term = f"%{search.strip()}%"
            query = query.where(
                or_(
                    cast(Recibos.idRecibo, String).ilike(term),
                    cast(Pedido.idPedido, String).ilike(term),
                    Usuario.nombre.ilike(term),
                    Usuario.apellido.ilike(term),
                    (Usuario.nombre + " " + Usuario.apellido).ilike(term),
                )
            )

        count_query = select(func.count()).select_from(query.order_by(None).subquery())
        total = db.scalar(count_query) or 0
        rows = db.execute(
            query.order_by(Recibos.fechaEmision.desc(), Recibos.idRecibo.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return {
            "items": [
                {
                    "idRecibo": receipt.idRecibo,
                    "fechaEmision": receipt.fechaEmision,
                    "totalPagar": receipt.totalPagar,
                    "pedido": {
                        "idPedido": order.idPedido,
                        "estadoPedido": order.estadoPedido,
                        "fechaHoraCreacion": order.fechaHoraCreacion,
                    },
                    "nombreCliente": f"{user.nombre} {user.apellido}",
                }
                for receipt, order, user in rows
            ],
            "pagina": page,
            "tamanoPagina": page_size,
            "total": total,
        }

    @staticmethod
    def get_receipt_detail(
        db: Session,
        receipt_id: int,
        current_user: Usuario,
    ) -> dict:
        receipt = db.scalar(
            select(Recibos)
            .where(Recibos.idRecibo == receipt_id)
            .options(
                selectinload(Recibos.pedido)
                .selectinload(Pedido.detalles_pedido)
                .selectinload(DetallePedido.producto),
                selectinload(Recibos.pedido)
                .selectinload(Pedido.cliente)
                .selectinload(Cliente.usuarios)
                .selectinload(Usuario.rol),
            )
        )
        if receipt is None:
            raise ReceiptNotFoundError("Recibo no encontrado.")

        order = receipt.pedido
        ReceiptService._assert_receipt_access(current_user, order)
        customer_user = next(
            (
                user
                for user in order.cliente.usuarios
                if user.rol.nombre == UserRole.CLIENTE.value
            ),
            None,
        )
        if customer_user is None:
            raise ReceiptConflictError(
                "No se encontró el usuario asociado al cliente del pedido."
            )

        return {
            "idRecibo": receipt.idRecibo,
            "fechaEmision": receipt.fechaEmision,
            "totalPagar": receipt.totalPagar,
            "pedido": {
                "idPedido": order.idPedido,
                "estadoPedido": order.estadoPedido,
                "fechaHoraCreacion": order.fechaHoraCreacion,
                "fechaHoraEntregaEstimada": order.fechaHoraEntregaEstimada,
            },
            "cliente": {
                "idCliente": order.cliente.idCliente,
                "nombre": customer_user.nombre,
                "apellido": customer_user.apellido,
                "correo": customer_user.correo,
                "telefono": customer_user.telefono,
                "direccion": order.cliente.direccion,
            },
            "productos": [
                {
                    "idProducto": line.producto_idProducto,
                    "nombreProducto": line.producto.nombre or "",
                    "cantidad": line.cantidad,
                    "precioUnitario": line.precioFijo,
                    "subtotal": line.precioFijo * line.cantidad,
                }
                for line in order.detalles_pedido
            ],
        }

    @staticmethod
    def _apply_visibility(query, current_user: Usuario):
        role = current_user.rol.nombre
        if role in (UserRole.ADMINISTRADOR.value, UserRole.SUPERADMIN.value):
            return query
        if role == UserRole.CLIENTE.value:
            if current_user.cliente_idCliente is None:
                raise ReceiptForbiddenError(
                    "La cuenta no tiene un perfil de cliente asociado."
                )
            return query.where(
                Pedido.cliente_idCliente == current_user.cliente_idCliente
            )
        if role == UserRole.DOMICILIARIO.value:
            if current_user.domiciliario_idDomiciliario is None:
                raise ReceiptForbiddenError(
                    "La cuenta no tiene un perfil de domiciliario asociado."
                )
            return query.where(
                Pedido.domiciliario_idDomiciliario
                == current_user.domiciliario_idDomiciliario
            )
        raise ReceiptForbiddenError("No tienes permisos para consultar recibos.")

    @staticmethod
    def _assert_receipt_access(current_user: Usuario, order: Pedido) -> None:
        role = current_user.rol.nombre
        if role in (UserRole.ADMINISTRADOR.value, UserRole.SUPERADMIN.value):
            return
        if (
            role == UserRole.CLIENTE.value
            and current_user.cliente_idCliente == order.cliente_idCliente
        ):
            return
        if (
            role == UserRole.DOMICILIARIO.value
            and current_user.domiciliario_idDomiciliario is not None
            and current_user.domiciliario_idDomiciliario
            == order.domiciliario_idDomiciliario
        ):
            return
        raise ReceiptForbiddenError("No tienes permisos para acceder a este recibo.")
