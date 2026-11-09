
from decimal import Decimal
from sqlalchemy import Integer, Numeric, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.infrastructure.database.base import Base


class DetallePedido(Base):

    __tablename__ = "detalles_pedidos"

    # Llave primaria
    idDetalle_Pedido: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    # Datos del detalle del pedido
    precioFijo: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    cantidad: Mapped[int] = mapped_column(Integer)

    # Llaves foráneas
    pedido_idPedido: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("pedidos.idPedido")
    )

    producto_idProducto: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("producto.idProducto")
    )
