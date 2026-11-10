"""A throwaway PostgreSQL database, migrated from zero, for the integration tests of the SQLAlchemy adapters.

The server comes from the TEST_DATABASE_* variables (a service container in CI). The test creates the same two
roles the installation has: the owner that runs the migrations and the application role the adapters use.
"""

import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, text

from autotrading.adapters.outbound.sqlalchemy.database import APPLICATION_ROLE, DatabaseSettings, create_database_engine

OWNER_ROLE = "autotrading_owner"
TEST_PASSWORD = "integration-only"  # noqa: S105 - throwaway role of a throwaway database
MIGRATIONS = Path(__file__).resolve().parents[2] / "migrations" / "alembic.ini"


def _server() -> tuple[str, int, str, str]:
    return (
        os.environ.get("TEST_DATABASE_HOST", "localhost"),
        int(os.environ.get("TEST_DATABASE_PORT", "5432")),
        os.environ.get("TEST_DATABASE_ADMIN", "postgres"),
        os.environ.get("TEST_DATABASE_ADMIN_PASSWORD", "postgres"),
    )


def _admin_engine(database: str) -> Engine:
    host, port, admin, password = _server()
    settings = DatabaseSettings(host=host, port=port, name=database, user=admin, password=password)
    return create_engine(settings.url(), isolation_level="AUTOCOMMIT")


def _ensure_roles(admin: Engine) -> None:
    with admin.connect() as connection:
        for role in (OWNER_ROLE, APPLICATION_ROLE):
            exists = connection.execute(text("SELECT 1 FROM pg_roles WHERE rolname = :role"), {"role": role}).first()
            if exists is None:
                connection.execute(text(f"CREATE ROLE {role} LOGIN PASSWORD '{TEST_PASSWORD}'"))


def _migrate(database: str, password_file: Path) -> None:
    host, port, _, _ = _server()
    password_file.write_text(TEST_PASSWORD, encoding="utf-8")
    variables = {
        "DATABASE_HOST": host,
        "DATABASE_PORT": str(port),
        "DATABASE_NAME": database,
        "DATABASE_OWNER": OWNER_ROLE,
        "DATABASE_OWNER_PASSWORD_FILE": str(password_file),
    }
    previous = {name: os.environ.get(name) for name in variables}
    os.environ.update(variables)
    try:
        command.upgrade(Config(str(MIGRATIONS)), "head")
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


@contextmanager
def migrated_database(workspace: Path) -> Iterator[Engine]:
    """Yields an engine connected as the application role to a new database with every migration applied."""
    host, port, _, _ = _server()
    database = f"autotrading_test_{uuid4().hex[:12]}"
    admin = _admin_engine("postgres")
    _ensure_roles(admin)
    with admin.connect() as connection:
        connection.execute(text(f"CREATE DATABASE {database} OWNER {OWNER_ROLE}"))
    try:
        _migrate(database, workspace / "owner-password")
        application = create_database_engine(
            DatabaseSettings(host=host, port=port, name=database, user=APPLICATION_ROLE, password=TEST_PASSWORD)
        )
        yield application
        application.dispose()
    finally:
        with admin.connect() as connection:
            connection.execute(text(f"DROP DATABASE IF EXISTS {database} WITH (FORCE)"))
        admin.dispose()
