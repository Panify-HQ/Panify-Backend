from sqlalchemy import Enum, Integer, String, Numeric, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base


class Productos(Base):

    __tablename__ = "productos"

    idProducto: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )

    nombre: Mapped[str] = mapped_column(String(45), nullable=False)

    precio: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    estado: Mapped[str] = mapped_column(Enum("Disponible", "Agotado"), nullable=False)

    descripcion: Mapped[str | None] = mapped_column(
        String(100), nullable=True, default=None, server_default=text("NULL")
    )

    detalles_pedido: Mapped[list["DetallePedido"]] = relationship(
        back_populates="producto"
    )

    inventarios: Mapped["Inventarios | None"] = relationship(
        back_populates="producto", uselist=False
    )

    movimientos: Mapped[list["Movimientos"]] = relationship(back_populates="producto")

    def __init__(
        self, nombre=None, precio=None, estado=None, descripcion=None, idProducto=None
    ):
        if idProducto is not None:
            self.idProducto = idProducto

        self.nombre = nombre
        self.precio = precio
        self.estado = estado
        self.descripcion = descripcion

    def json(self):
        return {
            "idProducto": self.idProducto,
            "nombre": self.nombre,
            "precio": self.precio,
            "estado": self.estado,
            "descripcion": self.descripcion,
        }

    def __str__(self):
        return (
            f"Productos(idProducto={self.idProducto}, "
            f"nombre={self.nombre}, precio={self.precio}, "
            f"estado={self.estado}, descripcion={self.descripcion})"
        )
