
from sqlalchemy import Integer, DateTime, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.infrastructure.database.base import Base


class Pedido(Base):

    __tablename__ = "pedidos"

    # Llave primaria
    idPedido: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    # Fechas del pedido
    fechaHoraCreacion: Mapped[DateTime] = mapped_column(DateTime)
    fechaHoraEntregaEstimada: Mapped[DateTime] = mapped_column(DateTime)

    # Estado del pedido
    estadoPedido: Mapped[str] = mapped_column(
        Enum("preparacion", "en_camino", "entregado", "cancelado")
    )

    # Llaves foráneas
    cliente_idCliente: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("cliente.idCliente")
    )

    domiciliario_idDomiciliario: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("domiciliario.idDomiciliario"),
        nullable=True
    )
