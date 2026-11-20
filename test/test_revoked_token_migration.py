import importlib.util
from pathlib import Path

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect

import app.models
from app.infrastructure.database.base import Base


def load_migration(filename: str):
    migration_path = Path(__file__).parents[1] / "migrations" / "versions" / filename
    spec = importlib.util.spec_from_file_location(filename, migration_path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    return migration


def test_revoked_token_migration_matches_models_and_downgrades():
    initial = load_migration(
        "89567ed79b5e_crear_esquema_inicial_completo.py"
    )
    revoked_tokens = load_migration("4f6c2a8d91b3_create_revoked_tokens.py")
    engine = create_engine("sqlite:///:memory:")

    with engine.begin() as connection:
        with Operations.context(MigrationContext.configure(connection)):
            initial.upgrade()
            revoked_tokens.upgrade()

        differences = compare_metadata(
            MigrationContext.configure(
                connection,
                opts={"compare_type": True, "compare_server_default": True},
            ),
            Base.metadata,
        )
        assert differences == []
        assert "revoked_tokens" in inspect(connection).get_table_names()

        with Operations.context(MigrationContext.configure(connection)):
            revoked_tokens.downgrade()
            initial.downgrade()

        assert inspect(connection).get_table_names() == []
