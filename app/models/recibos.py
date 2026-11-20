from datetime import datetime

from sqlalchemy import Integer, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base


class Recibos(Base):

    __tablename__ = "recibos"

    idRecibo: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    totalPagar: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    fechaEmision: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    pedido_idPedido: Mapped[int] = mapped_column(
        Integer, ForeignKey("pedidos.idPedido"), nullable=False, unique=True
    )

    pedido: Mapped["Pedido"] = relationship(back_populates="recibos")
