"""R6.6.1: the Entra settings the MCP client needs, applied by the script of the owner (Bug 738, ADR
impostazioni-entra-dell-accesso-mcp-riproducibili), on a fake `az` that keeps the state of the directory."""

from pathlib import Path

import pytest
from pytest_bdd import given, then, when

from tests.support.entra_installation import API_CLIENT_ID, EntraInstallation

API_IDENTIFIER = f"api://{API_CLIENT_ID}"
CONFIGURED_REDIRECT = "http://localhost/callback"


class Entra:
    def __init__(self, directory: Path) -> None:
        self.installation = EntraInstallation(directory)
        self.writes_before_rerun = 0
        self.identifiers_before_rerun: list[str] = []
        self.redirects_before_rerun: list[str] = []


@pytest.fixture
def entra(tmp_path: Path) -> Entra:
    return Entra(tmp_path)


@given("un'installazione appena preparata per l'accesso MCP")
def installation_just_prepared(entra: Entra) -> None:
    assert entra.installation.resource not in entra.installation.api_identifiers


@given("un'installazione con le impostazioni di accesso già applicate")
def installation_already_configured(entra: Entra) -> None:
    assert entra.installation.configure().status == 0


@when("il proprietario applica le impostazioni di accesso dell'installazione")
def owner_applies_settings(entra: Entra) -> None:
    assert entra.installation.configure().status == 0


@when("il proprietario le applica di nuovo")
def owner_applies_settings_again(entra: Entra) -> None:
    entra.writes_before_rerun = len(entra.installation.writes)
    entra.identifiers_before_rerun = entra.installation.api_identifiers
    entra.redirects_before_rerun = entra.installation.client_redirects
    assert entra.installation.configure().status == 0


@then("Entra riconosce il server MCP dell'installazione come risorsa dell'API")
def server_is_resource_of_api(entra: Entra) -> None:
    assert entra.installation.resource in entra.installation.api_identifiers


@then("gli accessi già concessi all'API restano validi")
def api_keeps_its_identifier(entra: Entra) -> None:
    assert API_IDENTIFIER in entra.installation.api_identifiers


@then("Entra rimanda l'accesso del client MCP solo al suo indirizzo di ritorno locale")
def client_returns_only_to_local_callback(entra: Entra) -> None:
    assert entra.installation.client_redirects == [CONFIGURED_REDIRECT]


@then("Entra non riceve alcuna modifica")
def nothing_changes(entra: Entra) -> None:
    assert entra.installation.api_identifiers == entra.identifiers_before_rerun
    assert entra.installation.client_redirects == entra.redirects_before_rerun
    assert len(entra.installation.writes) == entra.writes_before_rerun
