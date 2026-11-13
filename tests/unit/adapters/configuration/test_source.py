from pathlib import Path

import pytest

from autotrading.adapters.configuration.errors import InvalidConfigurationError, MissingConfigurationError
from autotrading.adapters.configuration.source import PROCESS_ENVIRONMENT, ConfigurationSource
from autotrading.domain.accounts.errors import UndeclaredEnvironmentError, UnsupportedEnvironmentError
from autotrading.domain.accounts.installation_environment import InstallationEnvironment


def _secret_file(tmp_path: Path, content: str) -> str:
    location = tmp_path / "secret"
    location.write_text(content, encoding="utf-8")
    return str(location)


def test_a_value_is_read_without_surrounding_spaces() -> None:
    assert ConfigurationSource({"APP_VERSION": " 1.2.0\n"}).value("APP_VERSION") == "1.2.0"


@pytest.mark.parametrize("values", [{}, {"APP_VERSION": "  "}], ids=["absent", "blank"])
def test_a_missing_value_names_the_variable(values: dict[str, str]) -> None:
    with pytest.raises(MissingConfigurationError) as raised:
        ConfigurationSource(values).value("APP_VERSION")

    assert raised.value.name == "APP_VERSION"
    assert str(raised.value) == "configurazione mancante: APP_VERSION"


@pytest.mark.parametrize("values", [{}, {"DATABASE_PORT": " "}], ids=["absent", "blank"])
def test_an_optional_value_not_declared_is_none(values: dict[str, str]) -> None:
    assert ConfigurationSource(values).optional("DATABASE_PORT") is None


def test_an_optional_value_declared_is_read_without_spaces() -> None:
    assert ConfigurationSource({"DATABASE_PORT": " 6543 "}).optional("DATABASE_PORT") == "6543"


def test_a_secret_is_read_from_the_file_its_variable_names(tmp_path: Path) -> None:
    source = ConfigurationSource({"DATABASE_PASSWORD_FILE": _secret_file(tmp_path, "s3cret\n")})

    assert source.secret("DATABASE_PASSWORD") == "s3cret"


@pytest.mark.parametrize("declared", [False, True], ids=["no-variable", "empty-file"])
def test_a_missing_secret_names_the_variable_of_its_file(tmp_path: Path, declared: bool) -> None:
    values = {"DATABASE_PASSWORD_FILE": _secret_file(tmp_path, "\n")} if declared else {}

    with pytest.raises(MissingConfigurationError) as raised:
        ConfigurationSource(values).secret("DATABASE_PASSWORD")

    assert raised.value.name == "DATABASE_PASSWORD_FILE"


def test_a_secret_file_that_does_not_exist_is_a_missing_configuration(tmp_path: Path) -> None:
    source = ConfigurationSource({"DATABASE_PASSWORD_FILE": str(tmp_path / "absent")})

    with pytest.raises(MissingConfigurationError) as raised:
        source.secret("DATABASE_PASSWORD")

    assert raised.value.name == "DATABASE_PASSWORD_FILE"


@pytest.mark.parametrize("case", ["no-variable", "no-file", "empty-file"])
def test_an_optional_secret_not_provided_is_none(tmp_path: Path, case: str) -> None:
    values = {
        "no-variable": {},
        "no-file": {"TELEGRAM_BOT_TOKEN_FILE": str(tmp_path / "absent")},
        "empty-file": {"TELEGRAM_BOT_TOKEN_FILE": _secret_file(tmp_path, " \n")},
    }[case]

    assert ConfigurationSource(values).optional_secret("TELEGRAM_BOT_TOKEN") is None


def test_an_optional_secret_provided_is_read(tmp_path: Path) -> None:
    source = ConfigurationSource({"TELEGRAM_BOT_TOKEN_FILE": _secret_file(tmp_path, "123:abc\n")})

    assert source.optional_secret("TELEGRAM_BOT_TOKEN") == "123:abc"


def test_the_environment_of_the_installation_is_declared_by_the_installation() -> None:
    assert ConfigurationSource({"APP_ENVIRONMENT": " prod\n"}).environment() is InstallationEnvironment.PROD


@pytest.mark.parametrize("values", [{}, {"APP_ENVIRONMENT": " "}], ids=["absent", "blank"])
def test_an_undeclared_environment_is_refused(values: dict[str, str]) -> None:
    with pytest.raises(UndeclaredEnvironmentError):
        ConfigurationSource(values).environment()


def test_an_unsupported_environment_is_refused() -> None:
    with pytest.raises(UnsupportedEnvironmentError) as raised:
        ConfigurationSource({"APP_ENVIRONMENT": "staging"}).environment()

    assert raised.value.environment == "staging"


def test_an_invalid_configuration_names_the_variable() -> None:
    error = InvalidConfigurationError("DATABASE_PORT")

    assert (error.name, str(error)) == ("DATABASE_PORT", "configurazione non valida: DATABASE_PORT")


def test_the_process_environment_is_the_live_environment_of_the_process(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTOTRADING_PROBE", "seen")

    assert PROCESS_ENVIRONMENT["AUTOTRADING_PROBE"] == "seen"
