from enum import Enum
from sqlalchemy import Enum as SAEnum, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class EstadoParada(str, Enum):
    PENDIENTE = "PENDIENTE"
    ENTREGADA = "ENTREGADA"
    FALLIDA = "FALLIDA"


class RutaParada(Base):
    __tablename__ = "rutasParada"

    idRutasParada: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    rutasEntrega_idRutasEntrega: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("rutasEntrega.idRutasEntrega", ondelete="CASCADE"),
        nullable=False
    )

    pedidos_idPedido: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("pedidos.idPedido", ondelete="CASCADE"),
        nullable=False
    )

    ordenEntrega: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    estadoParada: Mapped[EstadoParada] = mapped_column(
        SAEnum(
            EstadoParada,
            values_callable=lambda cls: [item.value for item in cls],
            native_enum=False,
            length=30,
            name="estado_parada",
        ),
        nullable=False
    )