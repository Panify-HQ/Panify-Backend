from datetime import datetime
from sqlalchemy import DateTime, Enum, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class Movimientos(Base):
    __tablename__ = "movimientos"

    idMovimiento: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )

    tipoMovimiento: Mapped[str] = mapped_column(
        Enum("ENTRADA", "SALIDA"), nullable=False
    )

    cantidad: Mapped[int] = mapped_column(Integer, nullable=False)

    fechaHora: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )

    panadero_idPanadero: Mapped[int] = mapped_column(
        Integer, ForeignKey("panaderos.idPanadero", ondelete="CASCADE"), nullable=False
    )

    producto_idProducto: Mapped[int] = mapped_column(
        Integer, ForeignKey("productos.idProducto", ondelete="CASCADE"), nullable=False
    )