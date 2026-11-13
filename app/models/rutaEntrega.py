from sqlalchemy import Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base


class RutaEntrega(Base):
    __tablename__ = "rutasEntrega"

    idRutasEntrega: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    estadoRuta: Mapped[str] = mapped_column(
        Enum("PENDIENTE", "EN_CURSO", "COMPLETADA", "CANCELADA"),
        nullable=False
    )

    urlRutaGoogle: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True
    )

    domiciliarios_idDomiciliario: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("domiciliario.idDomiciliario", ondelete="CASCADE"),
        nullable=False
    )

    domiciliario: Mapped["Domiciliario"] = relationship(
        back_populates="rutas_entrega"
    )
    paradas: Mapped[list["RutaParada"]] = relationship(
        back_populates="ruta_entrega"
    )