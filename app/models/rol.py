
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base


class Rol(Base):

    __tablename__ = "roles"

    idRol: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    nombre: Mapped[str] = mapped_column(
        String(45),
        nullable=False,
        unique=True
    )

    usuarios: Mapped[list["Usuario"]] = relationship(
        "Usuario",
        back_populates="rol"
    )
