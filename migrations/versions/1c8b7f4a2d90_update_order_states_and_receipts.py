"""Update order states and enforce one receipt per order.

Revision ID: 1c8b7f4a2d90
Revises: 4f6c2a8d91b3
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "1c8b7f4a2d90"
down_revision: Union[str, Sequence[str], None] = "4f6c2a8d91b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

OLD_STATES = ("preparacion", "en_camino", "entregado", "cancelado")
NEW_STATES = (
    "Pendiente",
    "En preparación",
    "Listo",
    "En camino",
    "Entregado",
    "Cancelado",
)


def _replace_order_state_column(
    state_mapping: dict[str, str],
    final_states: tuple[str, ...],
    temporary_column: str,
) -> None:
    op.add_column(
        "pedidos",
        sa.Column(temporary_column, sa.String(length=30), nullable=True),
    )
    orders = sa.table(
        "pedidos",
        sa.column("estadoPedido", sa.String()),
        sa.column(temporary_column, sa.String(length=30)),
    )
    op.execute(
        orders.update().values(
            {
                temporary_column: sa.case(
                    state_mapping,
                    value=orders.c.estadoPedido,
                )
            }
        )
    )

    if op.get_context().dialect.name == "sqlite":
        with op.batch_alter_table("pedidos") as batch_op:
            batch_op.drop_column("estadoPedido")
            batch_op.alter_column(
                temporary_column,
                new_column_name="estadoPedido",
                existing_type=sa.String(length=30),
                type_=sa.Enum(*final_states),
                existing_nullable=True,
                nullable=False,
            )
    else:
        op.drop_column("pedidos", "estadoPedido")
        op.alter_column(
            "pedidos",
            temporary_column,
            new_column_name="estadoPedido",
            existing_type=sa.String(length=30),
            type_=sa.Enum(*final_states),
            existing_nullable=True,
            nullable=False,
        )


def upgrade() -> None:
    _replace_order_state_column(
        {
            "preparacion": "En preparación",
            "en_camino": "En camino",
            "entregado": "Entregado",
            "cancelado": "Cancelado",
        },
        NEW_STATES,
        "estadoPedido_nuevo",
    )
    if op.get_context().dialect.name == "sqlite":
        with op.batch_alter_table("recibos") as batch_op:
            batch_op.create_unique_constraint(
                "uq_recibos_pedido_idPedido",
                ["pedido_idPedido"],
            )
    else:
        op.create_unique_constraint(
            "uq_recibos_pedido_idPedido",
            "recibos",
            ["pedido_idPedido"],
        )


def downgrade() -> None:
    if op.get_context().dialect.name == "sqlite":
        with op.batch_alter_table("recibos") as batch_op:
            batch_op.drop_constraint(
                "uq_recibos_pedido_idPedido",
                type_="unique",
            )
    else:
        op.drop_constraint(
            "uq_recibos_pedido_idPedido",
            "recibos",
            type_="unique",
        )

    _replace_order_state_column(
        {
            "Pendiente": "preparacion",
            "En preparación": "preparacion",
            "Listo": "preparacion",
            "En camino": "en_camino",
            "Entregado": "entregado",
            "Cancelado": "cancelado",
        },
        OLD_STATES,
        "estadoPedido_anterior",
    )
