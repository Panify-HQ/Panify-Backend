from sqlalchemy import Integer, String, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.infrastructure.database.base import Base


class Cliente(Base):

    __tablename__ = "cliente"

    # Llave primaria
    idCliente: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    # Tipo de cliente
    tipoCliente: Mapped[str] = mapped_column(
        Enum("Natural", "Jurídico"),
        nullable=False
    )

    # Dirección del cliente
    direccion: Mapped[str] = mapped_column(
        "dirección",
        String(150),
        nullable=False
    )

    usuarios: Mapped[list["Usuario"]] = relationship(back_populates="cliente")
    pedidos: Mapped[list["Pedido"]] = relationship(back_populates="cliente")
