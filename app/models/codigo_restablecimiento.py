from datetime import datetime

from sqlalchemy import (
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey
)
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class CodigoRestablecimiento(Base):

    __tablename__ = "codigo_restablecimiento"

    idCodigo: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    usuario_idUsuario: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("usuarios.idUsuario", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    codigo_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False
    )

    creado_en: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False
    )

    vence_en: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False
    )

    intentos: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )

    usado: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )