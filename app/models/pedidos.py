from datetime import datetime

from sqlalchemy import Integer, DateTime, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base


class Pedido(Base):

    __tablename__ = "pedidos"

    idPedido: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    fechaHoraCreacion: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    fechaHoraEntregaEstimada: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    estadoPedido: Mapped[str] = mapped_column(
        Enum(
            "Pendiente",
            "En preparación",
            "Listo",
            "En camino",
            "Entregado",
            "Cancelado",
        ),
        nullable=False,
    )

    cliente_idCliente: Mapped[int] = mapped_column(
        Integer, ForeignKey("clientes.idCliente"), nullable=False
    )

    domiciliario_idDomiciliario: Mapped[int] = mapped_column(
        Integer, ForeignKey("domiciliarios.idDomiciliario"), nullable=False
    )

    cliente: Mapped["Cliente"] = relationship(back_populates="pedidos")

    domiciliario: Mapped["Domiciliario"] = relationship(back_populates="pedidos")

    detalles_pedido: Mapped[list["DetallePedido"]] = relationship(
        back_populates="pedido"
    )

    recibos: Mapped["Recibos | None"] = relationship(
        back_populates="pedido", uselist=False
    )

    paradas_ruta: Mapped[list["RutaParada"]] = relationship(back_populates="pedido")
