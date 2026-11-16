
from sqlalchemy import Integer, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base


class Domiciliario(Base):

    __tablename__ = "domiciliarios"

    idDomiciliario: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=False
    )

    estadoDisponibilidad: Mapped[str] = mapped_column(
        Enum("Libre", "Ocupado", "Inactivo"),
        nullable=False
    )

    usuarios: Mapped[list["Usuario"]] = relationship(
        back_populates="domiciliario"
    )

    pedidos: Mapped[list["Pedido"]] = relationship(
        back_populates="domiciliario"
    )

    rutas_entrega: Mapped[list["RutaEntrega"]] = relationship(
        back_populates="domiciliario"
    )
