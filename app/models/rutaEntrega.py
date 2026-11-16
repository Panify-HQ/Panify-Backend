
from sqlalchemy import Integer, String, Enum, ForeignKey
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
        Enum("Pendiente", "En Curso", "Completada", "Cancelada"),
        nullable=False
    )

    urlRutaGoogle: Mapped[str] = mapped_column(
        String(500),
        nullable=False
    )

    domiciliarios_idDomiciliario: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("domiciliarios.idDomiciliario"),
        nullable=False
    )

    domiciliario: Mapped["Domiciliario"] = relationship(
        back_populates="rutas_entrega"
    )

    paradas: Mapped[list["RutaParada"]] = relationship(
        back_populates="ruta_entrega"
    )
