from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, Numeric, ForeignKey, DateTime, func
from app.infrastructure.database.base import Base


class Recibos(Base):
    __tablename__ = "recibos"

    idRecibo: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    totalPagar: Mapped[Decimal] = mapped_column(Numeric(10, 2))

    fechaEmision: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    pedido_idPedido: Mapped[int] = mapped_column(
        Integer, ForeignKey("pedidos.idPedido")
    )
