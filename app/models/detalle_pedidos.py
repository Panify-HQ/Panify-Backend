from sqlalchemy import Integer, Numeric, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base


class DetallePedido(Base):

    __tablename__ = "detalle_pedidos"

    idDetalle_Pedido: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )

    precioFijo: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    cantidad: Mapped[int] = mapped_column(Integer, nullable=False)

    pedido_idPedido: Mapped[int] = mapped_column(
        Integer, ForeignKey("pedidos.idPedido"), nullable=False
    )

    producto_idProducto: Mapped[int] = mapped_column(
        Integer, ForeignKey("productos.idProducto"), nullable=False
    )

    pedido: Mapped["Pedido"] = relationship(back_populates="detalles_pedido")

    producto: Mapped["Productos"] = relationship(back_populates="detalles_pedido")
