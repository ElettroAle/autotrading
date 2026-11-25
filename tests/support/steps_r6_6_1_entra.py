"""R6.6.1: the Entra settings the MCP client needs, applied by the script of the owner (Bug 738, ADR
impostazioni-entra-dell-accesso-mcp-riproducibili), on a fake `az` that keeps the state of the directory."""

from pathlib import Path

import pytest
from pytest_bdd import given, then, when

from tests.support.entra_installation import API_CLIENT_ID, EntraInstallation
from tests.support.steps import quoted

CLIENT_ID_PLACEHOLDER = "<client id>"
NAME_PLACEHOLDER = "<nome>"
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


@given(quoted('un\'installazione con il server MCP su "{resource}"'))
def installation_with_server(entra: Entra, resource: str) -> None:
    assert resource == entra.installation.resource.replace(entra.installation.name, NAME_PLACEHOLDER)


@given("un'installazione già configurata")
def installation_already_configured(entra: Entra) -> None:
    assert entra.installation.configure().status == 0


@when("lo script delle impostazioni Entra gira per l'installazione")
def script_runs(entra: Entra) -> None:
    assert entra.installation.configure().status == 0


@when("lo script gira di nuovo")
def script_runs_again(entra: Entra) -> None:
    entra.writes_before_rerun = len(entra.installation.writes)
    entra.identifiers_before_rerun = entra.installation.api_identifiers
    entra.redirects_before_rerun = entra.installation.client_redirects
    assert entra.installation.configure().status == 0


@then(quoted("l'applicazione dell'API ha tra i suoi identificativi \"{identifier}\""))
def api_has_identifier(entra: Entra, identifier: str) -> None:
    expected = identifier.replace(NAME_PLACEHOLDER, entra.installation.name)
    assert expected in entra.installation.api_identifiers


@then(quoted('conserva l\'identificativo "{identifier}"'))
def api_keeps_identifier(entra: Entra, identifier: str) -> None:
    assert identifier.replace(CLIENT_ID_PLACEHOLDER, API_CLIENT_ID) in entra.installation.api_identifiers


@then(quoted('il client MCP ha come unico redirect "{redirect}"'))
def client_has_only_redirect(entra: Entra, redirect: str) -> None:
    assert redirect == CONFIGURED_REDIRECT
    assert entra.installation.client_redirects == [redirect]


@then("identificativi e redirect non cambiano")
def nothing_changes(entra: Entra) -> None:
    assert entra.installation.api_identifiers == entra.identifiers_before_rerun
    assert entra.installation.client_redirects == entra.redirects_before_rerun
    assert len(entra.installation.writes) == entra.writes_before_rerun
