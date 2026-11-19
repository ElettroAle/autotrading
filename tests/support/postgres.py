"""A throwaway PostgreSQL database, migrated from zero, for the integration tests of the SQLAlchemy adapters.

The server comes from the TEST_DATABASE_* variables (a service container in CI). The test creates the same two
roles the installation has: the owner that runs the migrations and the application role the adapters use.
"""

import os
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config
from sqlalchemy import Connection, Engine, Executable, create_engine, event, inspect, text
from sqlalchemy.sql.dml import Insert
from sqlalchemy.util import immutabledict

from autotrading.adapters.outbound.sqlalchemy.database import APPLICATION_ROLE, SqlAlchemyDatabaseAdapter

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
    settings = SqlAlchemyDatabaseAdapter(host=host, port=port, name=database, user=admin, password=password)
    return create_engine(settings.url(), isolation_level="AUTOCOMMIT")


def _ensure_roles(admin: Engine) -> None:
    with admin.connect() as connection:
        for role in (OWNER_ROLE, APPLICATION_ROLE):
            exists = connection.execute(text("SELECT 1 FROM pg_roles WHERE rolname = :role"), {"role": role}).first()
            if exists is None:
                connection.execute(text(f"CREATE ROLE {role} LOGIN PASSWORD '{TEST_PASSWORD}'"))


def _migrate(database: str, password_file: Path, revision: str = "head") -> None:
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
        command.upgrade(Config(str(MIGRATIONS)), revision)
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


class _ColumnsOfTheRevision:
    """Keeps the inserts of the adapters within the columns the database has at its revision: a row saved at a past
    revision carries only what the platform saved then, not the columns a later migration adds to the current tables.
    """

    def __init__(self, engine: Engine) -> None:
        self._engine = engine
        self._columns: dict[str, frozenset[str]] = {}
        self.refresh()
        event.listen(engine, "before_execute", self._within_the_revision, retval=True)

    def refresh(self) -> None:
        inspector = inspect(self._engine)
        self._columns = {
            table: frozenset(column["name"] for column in inspector.get_columns(table))
            for table in inspector.get_table_names()
        }

    def _within_the_revision(
        self,
        _connection: Connection,
        statement: Executable,
        multiparams: object,
        params: object,
        _options: object,
    ) -> tuple[Executable, object, object]:
        if not isinstance(statement, Insert) or not statement._values:
            return statement, multiparams, params
        known = self._columns.get(statement.table.name)
        if known is None:
            return statement, multiparams, params
        values = {column: value for column, value in statement._values.items() if _name_of(column) in known}
        if len(values) == len(statement._values):
            return statement, multiparams, params
        # A copy of the same statement, so a returning or a conflict clause stays as the adapter wrote it.
        trimmed = statement._generate()
        trimmed._values = immutabledict(values)
        return trimmed, multiparams, params


def _name_of(column: object) -> str:
    return str(getattr(column, "key", column))


@contextmanager
def migrated_database(workspace: Path) -> Iterator[Engine]:
    """Yields an engine connected as the application role to a new database with every migration applied."""
    with database_migrated_to(workspace, "head") as (application, _):
        yield application


@contextmanager
def database_migrated_to(workspace: Path, revision: str) -> Iterator[tuple[Engine, Callable[[], None]]]:
    """Yields an engine connected as the application role to a new database migrated up to the revision, with the
    function that applies the migrations after it: what a migration does to the data saved before it.
    """
    host, port, _, _ = _server()
    database = f"autotrading_test_{uuid4().hex[:12]}"
    admin = _admin_engine("postgres")
    _ensure_roles(admin)
    with admin.connect() as connection:
        connection.execute(text(f"CREATE DATABASE {database} OWNER {OWNER_ROLE}"))
    try:
        _migrate(database, workspace / "owner-password", revision)
        application = SqlAlchemyDatabaseAdapter(
            host=host, port=port, name=database, user=APPLICATION_ROLE, password=TEST_PASSWORD
        ).engine()
        columns = _ColumnsOfTheRevision(application)

        def migrate_the_rest() -> None:
            _migrate(database, workspace / "owner-password")
            columns.refresh()

        yield application, migrate_the_rest
        application.dispose()
    finally:
        with admin.connect() as connection:
            connection.execute(text(f"DROP DATABASE IF EXISTS {database} WITH (FORCE)"))
        admin.dispose()


@contextmanager
def empty_database() -> Iterator[Engine]:
    """Yields an engine connected as the administrator to a new database without any migration."""
    database = f"autotrading_empty_{uuid4().hex[:12]}"
    admin = _admin_engine("postgres")
    with admin.connect() as connection:
        connection.execute(text(f"CREATE DATABASE {database}"))
    empty = _admin_engine(database)
    try:
        yield empty
    finally:
        empty.dispose()
        with admin.connect() as connection:
            connection.execute(text(f"DROP DATABASE IF EXISTS {database} WITH (FORCE)"))
        admin.dispose()
