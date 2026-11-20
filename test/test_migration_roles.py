import importlib.util
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, text


def test_initial_migration_seeds_roles_in_requested_order():
    migration_path = (
        Path(__file__).parents[1]
        / "migrations"
        / "versions"
        / "89567ed79b5e_crear_esquema_inicial_completo.py"
    )
    spec = importlib.util.spec_from_file_location("initial_migration", migration_path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()

        roles = connection.execute(
            text("SELECT idRol, nombre FROM roles ORDER BY idRol")
        ).all()

    assert roles == [
        (1, "Superadmin"),
        (2, "Administrador"),
        (3, "Panadero"),
        (4, "Domiciliario"),
        (5, "Cliente"),
    ]
