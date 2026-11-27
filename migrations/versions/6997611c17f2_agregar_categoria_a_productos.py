"""Agregar categoria a productos."""

from alembic import op
import sqlalchemy as sa


revision = "6997611c17f2"
down_revision = "1c8b7f4a2d90"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "productos",
        sa.Column("categoria", sa.String(length=250), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("productos", "categoria")