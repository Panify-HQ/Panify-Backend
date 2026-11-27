"""unir migraciones de inventario y restablecimiento

Revision ID: 0c82dcd68e73
Revises: 6997611c17f2, 89da0fea5b82
Create Date: 2026-11-27 06:55:57.803165

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0c82dcd68e73'
down_revision: Union[str, Sequence[str], None] = ('6997611c17f2', '89da0fea5b82')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
