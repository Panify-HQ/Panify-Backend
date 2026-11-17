from sqlalchemy import Integer, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base


class Panadero(Base):
    __tablename__ = "panaderos"

    idPanadero: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )

    estadoActividad: Mapped[str] = mapped_column(
        Enum("En Turno", "Descanso", "Inactivo"), nullable=False
    )

    usuarios: Mapped[list["Usuario"]] = relationship(back_populates="panadero")
    movimientos: Mapped[list["Movimientos"]] = relationship(back_populates="panadero")
