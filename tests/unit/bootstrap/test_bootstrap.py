from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from autotrading.bootstrap import (
    MissingConfigurationError,
    UndeclaredEnvironmentError,
    UnsupportedEnvironmentError,
    create_application,
)
from tests.support.installation import installation_configuration

AUTHENTICATION = {
    "AUTH_ISSUER": "https://login.example.test/tenant/v2.0",
    "AUTH_AUDIENCE": "api://autotrading",
    "AUTH_CLIENT_ID": "swagger-client",
    "AUTH_SCOPE": "api://autotrading/access",
}


def test_application_exposes_configured_version_and_environment(tmp_path: Path) -> None:
    application = create_application(installation_configuration(tmp_path, APP_VERSION="1.2.1", APP_ENVIRONMENT="prod"))

    response = TestClient(application).get("/health")

    assert response.json() == {"version": "1.2.1", "environment": "prod"}


def test_application_refuses_to_start_without_version(tmp_path: Path) -> None:
    with pytest.raises(MissingConfigurationError) as raised:
        create_application(installation_configuration(tmp_path, APP_VERSION="  "))

    assert raised.value.name == "APP_VERSION"
    assert str(raised.value) == "configurazione mancante: APP_VERSION"


@pytest.mark.parametrize("environment", [None, " "], ids=["absent", "blank"])
def test_application_refuses_to_start_without_environment(tmp_path: Path, environment: str | None) -> None:
    configuration = installation_configuration(tmp_path)
    if environment is None:
        del configuration["APP_ENVIRONMENT"]
    else:
        configuration["APP_ENVIRONMENT"] = environment

    with pytest.raises(UndeclaredEnvironmentError) as raised:
        create_application(configuration)

    assert str(raised.value) == "ambiente non dichiarato"


@pytest.mark.parametrize("environment", ["staging", "Dev", "production"])
def test_application_refuses_to_start_with_an_unsupported_environment(tmp_path: Path, environment: str) -> None:
    with pytest.raises(UnsupportedEnvironmentError) as raised:
        create_application(installation_configuration(tmp_path, APP_ENVIRONMENT=environment))

    assert raised.value.environment == environment
    assert str(raised.value) == "ambiente non ammesso: sono ammessi dev e prod"


def test_environment_is_accepted_with_surrounding_spaces(tmp_path: Path) -> None:
    application = create_application(installation_configuration(tmp_path, APP_ENVIRONMENT=" dev\n"))

    assert TestClient(application).get("/health").json()["environment"] == "dev"


@pytest.mark.parametrize("name", ["DATABASE_HOST", "DATABASE_NAME", "DATABASE_USER", "DATABASE_PASSWORD_FILE"])
def test_application_refuses_to_start_without_the_database(tmp_path: Path, name: str) -> None:
    with pytest.raises(MissingConfigurationError) as raised:
        create_application(installation_configuration(tmp_path, **{name: ""}))

    assert raised.value.name == name


def test_application_refuses_to_start_with_an_empty_database_secret(tmp_path: Path) -> None:
    configuration = installation_configuration(tmp_path)
    Path(configuration["DATABASE_PASSWORD_FILE"]).write_text("\n", encoding="utf-8")

    with pytest.raises(MissingConfigurationError) as raised:
        create_application(configuration)

    assert raised.value.name == "DATABASE_PASSWORD_FILE"


def test_without_an_issuer_every_protected_function_is_refused_as_not_configured(tmp_path: Path) -> None:
    client = TestClient(create_application(installation_configuration(tmp_path)))

    response = client.get("/me", headers={"Authorization": "Bearer any-token"})

    assert (response.status_code, response.json()) == (503, {"detail": "autenticazione non configurata"})


def test_with_an_issuer_the_openapi_page_logs_in_with_it(tmp_path: Path) -> None:
    client = TestClient(create_application(installation_configuration(tmp_path, **AUTHENTICATION)))

    schemes = client.get("/openapi.json").json()["components"]["securitySchemes"]

    assert schemes["OpenIdConnect"]["openIdConnectUrl"] == (
        "https://login.example.test/tenant/v2.0/.well-known/openid-configuration"
    )


@pytest.mark.parametrize("name", ["AUTH_AUDIENCE", "AUTH_CLIENT_ID", "AUTH_SCOPE"])
def test_an_issuer_without_the_rest_of_the_login_refuses_to_start(tmp_path: Path, name: str) -> None:
    with pytest.raises(MissingConfigurationError) as raised:
        create_application(installation_configuration(tmp_path, **{**AUTHENTICATION, name: " "}))

    assert raised.value.name == name
