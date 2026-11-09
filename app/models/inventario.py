from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class Inventario(Base):
    __tablename__ = "inventarios"

    idInventario: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    stockMinimo: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    stockActual: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    producto_idProducto: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("productos.idProducto", ondelete="CASCADE"),
        nullable=False
    )