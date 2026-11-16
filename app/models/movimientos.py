
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base


class Movimientos(Base):

    __tablename__ = "movimientos"

    idMovimiento: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    tipoMovimiento: Mapped[str] = mapped_column(
        Enum("Entrada", "Salida", "Ajuste"),
        nullable=False
    )

    cantidad: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    fechaHora: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False
    )

    panadero_idPanadero: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("panaderos.idPanadero"),
        nullable=False
    )

    producto_idProducto: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("productos.idProducto"),
        nullable=False
    )

    panadero: Mapped["Panadero"] = relationship(
        back_populates="movimientos"
    )

    producto: Mapped["Productos"] = relationship(
        back_populates="movimientos"
    )
