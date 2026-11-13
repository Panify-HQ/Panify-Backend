from sqlalchemy import Integer, String, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.infrastructure.database.base import Base


class Usuario(Base):

    __tablename__ = "usuario"

    # Llave primaria
    idUsuario: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    # Datos personales
    nombre: Mapped[str] = mapped_column(String(45))
    apellido: Mapped[str] = mapped_column(String(45))
    correo: Mapped[str] = mapped_column(String(150))
    contrasena: Mapped[str] = mapped_column("contraseña", String(255))
    telefono: Mapped[str] = mapped_column(String(15))

    # Estado del usuario
    estado: Mapped[str] = mapped_column(String(20))

    # Llaves foráneas
    Rol_idRol: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("rol.id")
    )

    cliente_idCliente: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("cliente.idCliente"),
        nullable=True
    )

    panadero_idPanadero: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("panadero.id"),
        nullable=True
    )

    domiciliario_idDomiciliario: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("domiciliario.idDomiciliario"),
        nullable=True
    )

    rol: Mapped["Rol"] = relationship(back_populates="usuarios")
    cliente: Mapped["Cliente | None"] = relationship(back_populates="usuarios")
    panadero: Mapped["Panadero | None"] = relationship(back_populates="usuarios")
    domiciliario: Mapped["Domiciliario | None"] = relationship(
        back_populates="usuarios"
    )
