from pathlib import Path

import pytest

from autotrading.adapters.configuration.errors import InvalidConfigurationError, MissingConfigurationError
from autotrading.adapters.configuration.source import ConfigurationSource
from autotrading.adapters.outbound.sqlalchemy.composition import sqlalchemy_adapters


def _database(tmp_path: Path, **overrides: str) -> ConfigurationSource:
    password = tmp_path / "password"
    password.write_text("s3cret\n", encoding="utf-8")
    values = {
        "DATABASE_HOST": "postgres",
        "DATABASE_NAME": "autotrading",
        "DATABASE_USER": "autotrading_app",
        "DATABASE_PASSWORD_FILE": str(password),
    }
    return ConfigurationSource(values | overrides)


def test_the_engine_reaches_the_declared_database_on_the_default_port(tmp_path: Path) -> None:
    url = sqlalchemy_adapters(_database(tmp_path)).url

    assert (url.host, url.port, url.database, url.username, url.password) == (
        "postgres",
        5432,
        "autotrading",
        "autotrading_app",
        "s3cret",
    )


def test_the_port_can_be_declared(tmp_path: Path) -> None:
    assert sqlalchemy_adapters(_database(tmp_path, DATABASE_PORT=" 6543 ")).url.port == 6543


@pytest.mark.parametrize("port", ["five", "0", "70000"])
def test_a_port_that_is_not_a_port_is_an_invalid_configuration(tmp_path: Path, port: str) -> None:
    with pytest.raises(InvalidConfigurationError) as raised:
        sqlalchemy_adapters(_database(tmp_path, DATABASE_PORT=port))

    assert raised.value.name == "DATABASE_PORT"


@pytest.mark.parametrize("name", ["DATABASE_HOST", "DATABASE_NAME", "DATABASE_USER", "DATABASE_PASSWORD_FILE"])
def test_the_database_must_be_declared(tmp_path: Path, name: str) -> None:
    with pytest.raises(MissingConfigurationError) as raised:
        sqlalchemy_adapters(_database(tmp_path, **{name: ""}))

    assert raised.value.name == name
