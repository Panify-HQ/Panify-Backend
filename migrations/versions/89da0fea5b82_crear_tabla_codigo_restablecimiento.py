"""crear tabla codigo restablecimiento

Revision ID: 89da0fea5b82
Revises: 4f6c2a8d91b3
Create Date: 2026-11-25 20:26:29.731099

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '89da0fea5b82'
down_revision: Union[str, Sequence[str], None] = '4f6c2a8d91b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """Crear tabla de códigos de restablecimiento."""

    op.create_table(
        'codigo_restablecimiento',

        sa.Column(
            'idCodigo',
            sa.Integer(),
            autoincrement=True,
            nullable=False
        ),

        sa.Column(
            'usuario_idUsuario',
            sa.Integer(),
            nullable=False
        ),

        sa.Column(
            'codigo_hash',
            sa.String(length=64),
            nullable=False
        ),

        sa.Column(
            'creado_en',
            sa.DateTime(),
            nullable=False
        ),

        sa.Column(
            'vence_en',
            sa.DateTime(),
            nullable=False
        ),

        sa.Column(
            'intentos',
            sa.Integer(),
            nullable=False
        ),

        sa.Column(
            'usado',
            sa.Boolean(),
            nullable=False
        ),

        sa.ForeignKeyConstraint(
            ['usuario_idUsuario'],
            ['usuarios.idUsuario'],
            ondelete='CASCADE'
        ),

        sa.PrimaryKeyConstraint('idCodigo')
    )

    op.create_index(
        'ix_codigo_restablecimiento_usuario_idUsuario',
        'codigo_restablecimiento',
        ['usuario_idUsuario'],
        unique=False
    )


def downgrade() -> None:
    """Eliminar tabla de códigos de restablecimiento."""

    op.drop_index(
        'ix_codigo_restablecimiento_usuario_idUsuario',
        table_name='codigo_restablecimiento'
    )

    op.drop_table('codigo_restablecimiento')