from sqlalchemy import Enum, ForeignKey, Integer, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base


class RutaParada(Base):

    __tablename__ = "rutasParada"

    idRutasParada: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )

    rutasEntrega_idRutasEntrega: Mapped[int] = mapped_column(
        Integer, ForeignKey("rutasEntrega.idRutasEntrega"), nullable=False
    )

    pedidos_idPedido: Mapped[int] = mapped_column(
        Integer, ForeignKey("pedidos.idPedido"), nullable=False
    )

    ordenEntrega: Mapped[int] = mapped_column(Integer, nullable=False)

    estadoParada: Mapped[str] = mapped_column(
        Enum("Pendiente", "Entregado", "Fallido"),
        nullable=False,
        default="Pendiente",
        server_default=text("'Pendiente'"),
    )

    ruta_entrega: Mapped["RutaEntrega"] = relationship(back_populates="paradas")

    pedido: Mapped["Pedido"] = relationship(back_populates="paradas_ruta")
