import importlib.util
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError


def load_migration(filename: str, module_name: str):
    path = Path(__file__).parents[1] / "migrations" / "versions" / filename
    spec = importlib.util.spec_from_file_location(module_name, path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    return migration


def test_order_state_and_receipt_unique_migration():
    initial = load_migration(
        "89567ed79b5e_crear_esquema_inicial_completo.py",
        "initial_receipt_migration",
    )
    revoked_tokens = load_migration(
        "4f6c2a8d91b3_create_revoked_tokens.py",
        "revoked_tokens_receipt_migration",
    )
    receipt_migration = load_migration(
        "1c8b7f4a2d90_update_order_states_and_receipts.py",
        "receipt_migration",
    )

    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        with Operations.context(MigrationContext.configure(connection)):
            initial.upgrade()
            revoked_tokens.upgrade()
            connection.execute(
                text(
                    """
                    INSERT INTO pedidos (
                        idPedido, fechaHoraCreacion, fechaHoraEntregaEstimada,
                        estadoPedido, cliente_idCliente
                    ) VALUES
                        (1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 'preparacion', 101),
                        (2, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 'en_camino', 102)
                    """
                )
            )
            receipt_migration.upgrade()

        states = (
            connection.execute(
                text("SELECT estadoPedido FROM pedidos ORDER BY idPedido")
            )
            .scalars()
            .all()
        )
        assert states == ["En preparación", "En camino"]

        unique_columns = [
            constraint["column_names"]
            for constraint in inspect(connection).get_unique_constraints("recibos")
        ]
        assert ["pedido_idPedido"] in unique_columns

        connection.execute(
            text(
                "INSERT INTO recibos (totalPagar, pedido_idPedido) " "VALUES (10.00, 1)"
            )
        )
        with pytest.raises(IntegrityError):
            connection.execute(
                text(
                    "INSERT INTO recibos (totalPagar, pedido_idPedido) "
                    "VALUES (15.00, 1)"
                )
            )
