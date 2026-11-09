from enum import Enum
from sqlalchemy import Enum as SAEnum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class EstadoRuta(str, Enum):
    PENDIENTE = "PENDIENTE"
    EN_CURSO = "EN_CURSO"
    COMPLETADA = "COMPLETADA"
    CANCELADA = "CANCELADA"


class RutaEntrega(Base):
    __tablename__ = "rutasEntrega"

    idRutasEntrega: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    estadoRuta: Mapped[EstadoRuta] = mapped_column(
        SAEnum(
            EstadoRuta,
            values_callable=lambda cls: [item.value for item in cls],
            native_enum=False,
            length=30,
            name="estado_ruta",
        ),
        nullable=False
    )

    urlRutaGoogle: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True
    )

    domiciliarios_idDomiciliario: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("domiciliarios.idDomiciliario", ondelete="CASCADE"),
        nullable=False
    )