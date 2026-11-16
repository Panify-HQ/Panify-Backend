
from sqlalchemy import Integer, Enum
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class Panadero(Base):
    __tablename__ = "panaderos"

    idPanadero: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    estadoActividad: Mapped[str] = mapped_column(
        Enum("En Turno", "Descanso", "Inactivo"),
        nullable=False
    )
