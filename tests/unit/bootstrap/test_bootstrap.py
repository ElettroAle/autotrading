import pytest
from fastapi.testclient import TestClient

from autotrading.bootstrap import (
    MissingConfigurationError,
    UndeclaredEnvironmentError,
    UnsupportedEnvironmentError,
    create_application,
)


def test_application_exposes_configured_version_and_environment() -> None:
    application = create_application({"APP_VERSION": "1.2.1", "APP_ENVIRONMENT": "prod"})

    response = TestClient(application).get("/health")

    assert response.json() == {"version": "1.2.1", "environment": "prod"}


def test_application_refuses_to_start_without_version() -> None:
    with pytest.raises(MissingConfigurationError) as raised:
        create_application({"APP_VERSION": "  ", "APP_ENVIRONMENT": "prod"})

    assert raised.value.name == "APP_VERSION"
    assert str(raised.value) == "configurazione mancante: APP_VERSION"


@pytest.mark.parametrize("configuration", [{"APP_VERSION": "1.2.1"}, {"APP_VERSION": "1.2.1", "APP_ENVIRONMENT": " "}])
def test_application_refuses_to_start_without_environment(configuration: dict[str, str]) -> None:
    with pytest.raises(UndeclaredEnvironmentError) as raised:
        create_application(configuration)

    assert str(raised.value) == "ambiente non dichiarato"


@pytest.mark.parametrize("environment", ["staging", "Dev", "production"])
def test_application_refuses_to_start_with_an_unsupported_environment(environment: str) -> None:
    with pytest.raises(UnsupportedEnvironmentError) as raised:
        create_application({"APP_VERSION": "1.2.1", "APP_ENVIRONMENT": environment})

    assert raised.value.environment == environment
    assert str(raised.value) == "ambiente non ammesso: sono ammessi dev e prod"


def test_environment_is_accepted_with_surrounding_spaces() -> None:
    application = create_application({"APP_VERSION": "1.2.1", "APP_ENVIRONMENT": " dev\n"})

    assert TestClient(application).get("/health").json()["environment"] == "dev"
