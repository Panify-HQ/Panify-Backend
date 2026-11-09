from datetime import datetime
from enum import Enum
from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class TipoMovimiento(str, Enum):
    ENTRADA = "ENTRADA"
    SALIDA = "SALIDA"


class Movimiento(Base):
    __tablename__ = "movimientos"

    idMovimiento: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    tipoMovimiento: Mapped[TipoMovimiento] = mapped_column(
        SAEnum(
            TipoMovimiento,
            values_callable=lambda cls: [item.value for item in cls],
            native_enum=False,
            length=20,
            name="tipo_movimiento",
        ),
        nullable=False
    )

    cantidad: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    fechaHora: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp()
    )

    panadero_idPanadero: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("panaderos.idPanadero", ondelete="CASCADE"),
        nullable=False
    )

    producto_idProducto: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("productos.idProducto", ondelete="CASCADE"),
        nullable=False
    )