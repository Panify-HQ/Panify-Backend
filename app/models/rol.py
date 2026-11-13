from sqlalchemy import Integer, String, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.infrastructure.database.base import Base


class Rol(Base):

    __tablename__ = "rol"

    # Llave primaria
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    # nombre
    nombre: Mapped[str] = mapped_column(
        String(45)
    )

    usuarios: Mapped[list["Usuario"]] = relationship(back_populates="rol")

