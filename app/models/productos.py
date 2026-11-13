from sqlalchemy import Enum, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base


class Productos(Base):
    __tablename__ = "productos"

    idProducto: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    nombre: Mapped[str | None] = mapped_column(String(250), nullable=True)
    precio: Mapped[float | None] = mapped_column(Float, nullable=True)
    estado: Mapped[str | None] = mapped_column(
        Enum("ACTIVO", "INACTIVO", "AGOTADO"), nullable=True
    )
    descripcion: Mapped[str | None] = mapped_column(String(250), nullable=True)

    detalles_pedido: Mapped[list["DetallePedido"]] = relationship(
        back_populates="producto"
    )
    inventarios: Mapped[list["Inventarios"]] = relationship(back_populates="producto")
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
        return f"Productos(idProducto={self.idProducto}, nombre={self.nombre}, precio={self.precio}, estado={self.estado}, descripcion={self.descripcion})"

