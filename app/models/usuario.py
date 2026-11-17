from sqlalchemy import Integer, String, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base


class Usuario(Base):

    __tablename__ = "usuarios"

    idUsuario: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )

    nombre: Mapped[str] = mapped_column(String(45), nullable=False)

    apellido: Mapped[str] = mapped_column(String(45), nullable=False)

    correo: Mapped[str] = mapped_column(String(150), nullable=False, unique=True)

    contrasena: Mapped[str] = mapped_column(String(255), nullable=False)

    telefono: Mapped[str] = mapped_column(String(15), nullable=False)

    estado: Mapped[str] = mapped_column(Enum("Activo", "Inactivo"), nullable=False)

    Rol_idRol: Mapped[int] = mapped_column(
        Integer, ForeignKey("roles.idRol"), nullable=False
    )

    cliente_idCliente: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("clientes.idCliente"), nullable=True, unique=True
    )

    panadero_idPanadero: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("panaderos.idPanadero"), nullable=True, unique=True
    )

    domiciliario_idDomiciliario: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("domiciliarios.idDomiciliario"), nullable=True, unique=True
    )

    rol: Mapped["Rol"] = relationship("Rol", back_populates="usuarios")
