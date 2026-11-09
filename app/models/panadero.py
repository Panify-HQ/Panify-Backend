
from sqlalchemy import Integer, String, Enum
from sqlalchemy.orm import Mapped, mapped_column
from app.infrastructure.database.base import Base


class panadero(Base):

    __tablename__ = "panadero"

    # Llave primaria
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    # nombre
    estadoActividad: Mapped[str] = mapped_column(
        Enum("En Turno", "Descanso","Inactivo"),
               nullable=False
           
    )

   
