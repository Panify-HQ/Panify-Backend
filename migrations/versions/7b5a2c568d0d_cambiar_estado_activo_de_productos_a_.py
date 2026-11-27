"""cambiar estado activo de productos a disponible

Revision ID: 7b5a2c568d0d
Revises: 0c82dcd68e73
Create Date: 2026-11-27 07:13:28.478816

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7b5a2c568d0d'
down_revision: Union[str, Sequence[str], None] = '0c82dcd68e73'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE productos MODIFY COLUMN estado "
        "ENUM('ACTIVO', 'INACTIVO', 'AGOTADO', 'Disponible') NULL"
    )
    op.execute(
        "UPDATE productos SET estado = 'Disponible' WHERE estado = 'ACTIVO'"
    )
    op.execute(
        "ALTER TABLE productos MODIFY COLUMN estado "
        "ENUM('Disponible', 'INACTIVO', 'AGOTADO') NULL"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE productos MODIFY COLUMN estado "
        "ENUM('Disponible', 'INACTIVO', 'AGOTADO', 'ACTIVO') NULL"
    )
    op.execute(
        "UPDATE productos SET estado = 'ACTIVO' WHERE estado = 'Disponible'"
    )
    op.execute(
        "ALTER TABLE productos MODIFY COLUMN estado "
        "ENUM('ACTIVO', 'INACTIVO', 'AGOTADO') NULL"
    )