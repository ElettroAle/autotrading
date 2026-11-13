"""The engine of the database of the installation, from where it is and who connects (ADR 0015)."""

import pytest

from autotrading.adapters.outbound.sqlalchemy.composition import sqlalchemy_adapters
from autotrading.adapters.outbound.sqlalchemy.configuration import _SqlAlchemySettings

PASSWORD = "s3cret-password"  # noqa: S105 - a fake password of the tests


@pytest.mark.parametrize(("port", "expected"), [(None, 5432), ("6543", 6543)])
def test_the_engine_reaches_the_declared_database(port: str | None, expected: int) -> None:
    engine = sqlalchemy_adapters("db", port, "autotrading", "app", PASSWORD)

    assert (engine.url.host, engine.url.port, engine.url.database, engine.url.username) == (
        "db",
        expected,
        "autotrading",
        "app",
    )
    assert PASSWORD not in repr(engine)


def test_the_password_never_appears_in_the_settings_repr() -> None:
    assert PASSWORD not in repr(_SqlAlchemySettings("db", "autotrading", "app", PASSWORD))
