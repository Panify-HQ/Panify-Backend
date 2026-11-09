from enum import Enum
from sqlalchemy import Float, Integer, String, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


# 1. Definimos los posibles valores del Enum para el estado
class EstadoProducto(str, Enum):
    ACTIVO = "ACTIVO"
    INACTIVO = "INACTIVO"
    AGOTADO = "AGOTADO"


class Productos(Base):
    __tablename__ = 'productos'

    idProducto: Mapped[int] = mapped_column(
        Integer, 
        primary_key=True, 
        autoincrement=True
    )
    nombre: Mapped[str | None] = mapped_column(
        String(250), 
        nullable=True
    )
    precio: Mapped[float | None] = mapped_column(
        Float, 
        nullable=True
    )
    
    # 2. Aplicamos el Enum al campo estado
    estado: Mapped[EstadoProducto | None] = mapped_column(
        SAEnum(
            EstadoProducto,
            values_callable=lambda cls: [item.value for item in cls],
            native_enum=False,
            length=50,
            name="estado_producto",
        ),
        nullable=True
    )
    
    descripcion: Mapped[str | None] = mapped_column(
        String(250), 
        nullable=True
    )

    def __init__(self, nombre=None, precio=None, estado=None, descripcion=None, idProducto=None):
        if idProducto is not None:
            self.idProducto = idProducto
        self.nombre = nombre
        self.precio = precio
        self.estado = estado
        self.descripcion = descripcion

    def json(self):
        return {
            'idProducto': self.idProducto,
            'nombre': self.nombre,
            'precio': self.precio,
            'estado': self.estado.value if self.estado else None,
            'descripcion': self.descripcion
        }

    def __str__(self):
        return f"Productos(idProducto={self.idProducto}, nombre={self.nombre}, precio={self.precio}, estado={self.estado}, descripcion={self.descripcion})"