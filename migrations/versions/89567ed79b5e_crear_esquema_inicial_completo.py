"""crear esquema inicial completo

Revision ID: 89567ed79b5e
Revises: 
Create Date: 2026-11-12 22:03:27.941229

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '89567ed79b5e'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "clientes",
        sa.Column("idCliente", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column(
            "tipoCliente",
            sa.Enum("Nuevo", "Frecuente", "Ocasional"),
            nullable=False,
        ),
        sa.Column("direccion", sa.String(length=150), nullable=False),
        sa.PrimaryKeyConstraint("idCliente"),
    )
    op.create_table(
        "domiciliarios",
        sa.Column(
            "idDomiciliario", sa.Integer(), autoincrement=False, nullable=False
        ),
        sa.Column(
            "estadoDisponibilidad",
            sa.Enum("Libre", "Ocupado", "Inactivo"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("idDomiciliario"),
    )
    op.create_table(
        "panaderos",
        sa.Column("idPanadero", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column(
            "estadoActividad",
            sa.Enum("En turno", "Descanso", "Inactivo"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("idPanadero"),
    )
    op.create_table(
        "productos",
        sa.Column("idProducto", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("nombre", sa.String(length=45), nullable=False),
        sa.Column("precio", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column(
            "estado", sa.Enum("Disponible", "Agotado"), nullable=False
        ),
        sa.Column(
            "descripcion",
            sa.String(length=100),
            server_default=sa.text("NULL"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("idProducto"),
    )
    op.create_table(
        "roles",
        sa.Column("idRol", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("nombre", sa.String(length=45), nullable=False),
        sa.PrimaryKeyConstraint("idRol"),
        sa.UniqueConstraint("nombre"),
    )
    op.create_table(
        "inventarios",
        sa.Column("idInventario", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("stockMinimo", sa.Integer(), nullable=False),
        sa.Column("stockActual", sa.Integer(), nullable=False),
        sa.Column("producto_idProducto", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["producto_idProducto"], ["productos.idProducto"]
        ),
        sa.PrimaryKeyConstraint("idInventario"),
        sa.UniqueConstraint("producto_idProducto"),
    )
    op.create_table(
        "movimientos",
        sa.Column("idMovimiento", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "tipoMovimiento",
            sa.Enum("Entrada", "Salida", "Ajuste"),
            nullable=False,
        ),
        sa.Column("cantidad", sa.Integer(), nullable=False),
        sa.Column("fechaHora", sa.DateTime(), nullable=False),
        sa.Column("panadero_idPanadero", sa.Integer(), nullable=False),
        sa.Column("producto_idProducto", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["panadero_idPanadero"], ["panaderos.idPanadero"]
        ),
        sa.ForeignKeyConstraint(
            ["producto_idProducto"], ["productos.idProducto"]
        ),
        sa.PrimaryKeyConstraint("idMovimiento"),
    )
    op.create_table(
        "pedidos",
        sa.Column("idPedido", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("fechaHoraCreacion", sa.DateTime(), nullable=False),
        sa.Column("fechaHoraEntregaEstimada", sa.DateTime(), nullable=False),
        sa.Column(
            "estadoPedido",
            sa.Enum(
                "Pendiente",
                "En preparación",
                "Listo",
                "En camino",
                "Entregado",
                "Cancelado",
            ),
            nullable=False,
        ),
        sa.Column("cliente_idCliente", sa.Integer(), nullable=False),
        sa.Column("domiciliario_idDomiciliario", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["cliente_idCliente"], ["clientes.idCliente"]
        ),
        sa.ForeignKeyConstraint(
            ["domiciliario_idDomiciliario"], ["domiciliarios.idDomiciliario"]
        ),
        sa.PrimaryKeyConstraint("idPedido"),
    )
    op.create_table(
        "rutasEntrega",
        sa.Column("idRutasEntrega", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "estadoRuta",
            sa.Enum("Pendiente", "En Curso", "Completada", "Cancelada"),
            nullable=False,
        ),
        sa.Column("urlRutaGoogle", sa.String(length=500), nullable=False),
        sa.Column("domiciliarios_idDomiciliario", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["domiciliarios_idDomiciliario"], ["domiciliarios.idDomiciliario"]
        ),
        sa.PrimaryKeyConstraint("idRutasEntrega"),
    )
    op.create_table(
        "usuarios",
        sa.Column("idUsuario", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("nombre", sa.String(length=45), nullable=False),
        sa.Column("apellido", sa.String(length=45), nullable=False),
        sa.Column("correo", sa.String(length=150), nullable=False),
        sa.Column("contrasena", sa.String(length=255), nullable=False),
        sa.Column(
            "telefono", sa.String(length=15), nullable=False
        ),
        sa.Column(
            "estado", sa.Enum("Activo", "Inactivo"), nullable=False
        ),
        sa.Column("Rol_idRol", sa.Integer(), nullable=False),
        sa.Column("cliente_idCliente", sa.Integer(), nullable=True),
        sa.Column("panadero_idPanadero", sa.Integer(), nullable=True),
        sa.Column("domiciliario_idDomiciliario", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["Rol_idRol"], ["roles.idRol"]),
        sa.ForeignKeyConstraint(["cliente_idCliente"], ["clientes.idCliente"]),
        sa.ForeignKeyConstraint(
            ["domiciliario_idDomiciliario"], ["domiciliarios.idDomiciliario"]
        ),
        sa.ForeignKeyConstraint(
            ["panadero_idPanadero"], ["panaderos.idPanadero"]
        ),
        sa.PrimaryKeyConstraint("idUsuario"),
        sa.UniqueConstraint("correo"),
        sa.UniqueConstraint("cliente_idCliente"),
        sa.UniqueConstraint("panadero_idPanadero"),
        sa.UniqueConstraint("domiciliario_idDomiciliario"),
    )
    op.create_table(
        "detalle_pedidos",
        sa.Column(
            "idDetalle_Pedido", sa.Integer(), autoincrement=True, nullable=False
        ),
        sa.Column("precioFijo", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("cantidad", sa.Integer(), nullable=False),
        sa.Column("pedido_idPedido", sa.Integer(), nullable=False),
        sa.Column("producto_idProducto", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["pedido_idPedido"], ["pedidos.idPedido"]),
        sa.ForeignKeyConstraint(["producto_idProducto"], ["productos.idProducto"]),
        sa.PrimaryKeyConstraint("idDetalle_Pedido"),
    )
    op.create_table(
        "recibos",
        sa.Column("idRecibo", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("totalPagar", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("fechaEmision", sa.DateTime(), nullable=False),
        sa.Column("pedido_idPedido", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["pedido_idPedido"], ["pedidos.idPedido"]),
        sa.PrimaryKeyConstraint("idRecibo"),
        sa.UniqueConstraint("pedido_idPedido"),
    )
    op.create_table(
        "rutasParada",
        sa.Column("idRutasParada", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("rutasEntrega_idRutasEntrega", sa.Integer(), nullable=False),
        sa.Column("pedidos_idPedido", sa.Integer(), nullable=False),
        sa.Column("ordenEntrega", sa.Integer(), nullable=False),
        sa.Column(
            "estadoParada",
            sa.Enum("Pendiente", "Entregado", "Fallido"),
            server_default=sa.text("'Pendiente'"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["pedidos_idPedido"], ["pedidos.idPedido"]
        ),
        sa.ForeignKeyConstraint(
            ["rutasEntrega_idRutasEntrega"], ["rutasEntrega.idRutasEntrega"]
        ),
        sa.PrimaryKeyConstraint("idRutasParada"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("rutasParada")
    op.drop_table("recibos")
    op.drop_table("detalle_pedidos")
    op.drop_table("usuarios")
    op.drop_table("rutasEntrega")
    op.drop_table("pedidos")
    op.drop_table("movimientos")
    op.drop_table("inventarios")
    op.drop_table("roles")
    op.drop_table("productos")
    op.drop_table("panaderos")
    op.drop_table("domiciliarios")
    op.drop_table("clientes")
