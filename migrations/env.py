"""Alembic environment. Runs as the database owner, which the application role never is (row level security)."""

import os
from pathlib import Path

from alembic import context

from autotrading.adapters.outbound.sqlalchemy.database import SqlAlchemyDatabaseAdapter
from autotrading.adapters.outbound.sqlalchemy.tables import metadata


def owner_database() -> SqlAlchemyDatabaseAdapter:
    return SqlAlchemyDatabaseAdapter(
        host=os.environ["DATABASE_HOST"],
        port=int(os.environ.get("DATABASE_PORT", "5432")),
        name=os.environ["DATABASE_NAME"],
        user=os.environ["DATABASE_OWNER"],
        # Secrets arrive as read-only mounted files, never as environment values.
        password=Path(os.environ["DATABASE_OWNER_PASSWORD_FILE"]).read_text(encoding="utf-8").strip(),
    )


def run_migrations() -> None:
    engine = owner_database().engine()
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=metadata)
        with context.begin_transaction():
            context.run_migrations()


run_migrations()
