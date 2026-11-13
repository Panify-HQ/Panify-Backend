
from sqlalchemy import Integer, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.infrastructure.database.base import Base


class Domiciliario(Base):

    __tablename__ = "domiciliario"

    # Llave primaria
    idDomiciliario: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    # Estado de disponibilidad
    estadoDisponibilidad: Mapped[str] = mapped_column(
        Enum("Disponible", "No disponible", "Ocupado"),
        nullable=False
    )

    usuarios: Mapped[list["Usuario"]] = relationship(back_populates="domiciliario")
    pedidos: Mapped[list["Pedido"]] = relationship(back_populates="domiciliario")
    rutas_entrega: Mapped[list["RutaEntrega"]] = relationship(
        back_populates="domiciliario"
    )
