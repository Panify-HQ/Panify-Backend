from sqlalchemy import Integer, DateTime, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.infrastructure.database.base import Base


class Pedido(Base):

    __tablename__ = "pedidos"

    # Llave primaria
    idPedido: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Fechas del pedido
    fechaHoraCreacion: Mapped[DateTime] = mapped_column(DateTime)
    fechaHoraEntregaEstimada: Mapped[DateTime] = mapped_column(DateTime)

    # Estado del pedido
    estadoPedido: Mapped[str] = mapped_column(
        Enum(
            "Pendiente",
            "En preparación",
            "Listo",
            "En camino",
            "Entregado",
            "Cancelado",
        )
    )

    # Llaves foráneas
    cliente_idCliente: Mapped[int] = mapped_column(
        Integer, ForeignKey("clientes.idCliente")
    )

    domiciliario_idDomiciliario: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("domiciliarios.idDomiciliario"), nullable=True
    )

    cliente: Mapped["Cliente"] = relationship(back_populates="pedidos")
    domiciliario: Mapped["Domiciliario | None"] = relationship(back_populates="pedidos")
    detalles_pedido: Mapped[list["DetallePedido"]] = relationship(
        back_populates="pedido"
    )
    recibo: Mapped["Recibos | None"] = relationship(
        back_populates="pedido", uselist=False
    )
    paradas_ruta: Mapped[list["RutaParada"]] = relationship(back_populates="pedido")
