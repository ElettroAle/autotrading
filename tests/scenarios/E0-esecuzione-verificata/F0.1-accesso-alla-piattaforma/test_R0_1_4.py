from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pytest_bdd import given, parsers, scenarios, then, when

from autotrading.adapters.inbound.api.app import ENVIRONMENT_HEADER
from autotrading.bootstrap import create_application
from autotrading.domain.errors import AutotradingError
from tests.support.installation import installation_configuration

scenarios("E0-esecuzione-verificata/F0.1-accesso-alla-piattaforma/R0.1.4-ambiente-di-installazione-visibile.feature")


@pytest.fixture
def configuration(tmp_path: Path) -> dict[str, str]:
    configuration = installation_configuration(tmp_path)
    del configuration["APP_ENVIRONMENT"]
    return configuration


@given(parsers.parse("che l'installazione è configurata con l'ambiente \"{environment}\""))
def configured_environment(configuration: dict[str, str], environment: str) -> None:
    configuration["APP_ENVIRONMENT"] = environment


@given("che la configurazione dell'installazione non dichiara l'ambiente")
def undeclared_environment(configuration: dict[str, str]) -> None:
    configuration.pop("APP_ENVIRONMENT", None)


@given(parsers.parse("che la configurazione dell'installazione dichiara l'ambiente \"{environment}\""))
def declared_environment(configuration: dict[str, str], environment: str) -> None:
    configuration["APP_ENVIRONMENT"] = environment


@when("un utente riceve una qualunque risposta dalla piattaforma", target_fixture="responses")
def any_response(configuration: dict[str, str]) -> list[dict[str, str]]:
    client = TestClient(create_application(configuration))
    # A working function and a missing one: both answers must carry the environment.
    return [dict(client.get("/health").headers), dict(client.get("/funzione-inesistente").headers)]


@when("l'installazione viene avviata", target_fixture="startup_error")
def start_installation(configuration: dict[str, str]) -> AutotradingError:
    with pytest.raises(AutotradingError) as raised:
        create_application(configuration)
    return raised.value


@then(parsers.parse('la risposta riporta il nome dell\'ambiente "{environment}"'))
def response_reports_environment(responses: list[dict[str, str]], environment: str) -> None:
    assert [headers.get(ENVIRONMENT_HEADER.lower()) for headers in responses] == [environment, environment]


@then(parsers.parse('l\'avvio fallisce con il motivo "{reason}"'))
def startup_fails(startup_error: AutotradingError, reason: str) -> None:
    assert str(startup_error) == reason
