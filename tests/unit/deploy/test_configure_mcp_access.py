"""The Entra settings of the MCP access, applied once per installation by the owner (Bug 738).

ADR-impostazioni-entra-dell-accesso-mcp-riproducibili: the script runs against an `az` that logs its calls and keeps
its state; the pipeline never touches Entra.
"""

from pathlib import Path

import pytest

from tests.support.entra_installation import (
    API_CLIENT_ID,
    MCP_CLIENT_ID,
    REDIRECT_BEFORE_THE_FIX,
    EntraInstallation,
)

REDIRECT = "http://localhost/callback"


@pytest.fixture
def installation(tmp_path: Path) -> EntraInstallation:
    return EntraInstallation(tmp_path)


def test_adr_impostazioni_entra_adds_the_public_url_of_the_server_keeping_the_existing_identifier(
    installation: EntraInstallation,
) -> None:
    run = installation.configure()

    assert run.status == 0, run.output
    assert installation.api_identifiers == [f"api://{API_CLIENT_ID}", installation.resource]


def test_adr_impostazioni_entra_keeps_every_identifier_the_application_already_has(
    installation: EntraInstallation,
) -> None:
    installation.seed(API_CLIENT_ID, "identifierUris", [f"api://{API_CLIENT_ID}", "https://other.example/api"])

    installation.configure()

    assert installation.api_identifiers == [
        f"api://{API_CLIENT_ID}",
        "https://other.example/api",
        installation.resource,
    ]


def test_adr_impostazioni_entra_sets_the_redirect_with_the_path_as_the_only_one(
    installation: EntraInstallation,
) -> None:
    assert installation.client_redirects == [REDIRECT_BEFORE_THE_FIX]

    installation.configure()

    assert installation.client_redirects == [REDIRECT]


def test_adr_impostazioni_entra_writes_nothing_on_an_installation_already_configured(
    installation: EntraInstallation,
) -> None:
    installation.configure()
    writes_of_the_first_run = len(installation.writes)

    run = installation.configure()

    assert run.status == 0, run.output
    assert len(installation.writes) == writes_of_the_first_run
    assert "in ordine" in run.output


def test_adr_impostazioni_entra_tells_in_italian_what_it_changed(installation: EntraInstallation) -> None:
    run = installation.configure()

    assert "aggiunto" in run.output
    assert installation.resource in run.output
    assert REDIRECT in run.output


def test_adr_impostazioni_entra_writes_only_the_setting_that_is_wrong(installation: EntraInstallation) -> None:
    installation.seed(MCP_CLIENT_ID, "publicClient.redirectUris", [REDIRECT])

    installation.configure()

    assert [write for write in installation.writes if MCP_CLIENT_ID in write] == []
    assert len(installation.writes) == 1


@pytest.mark.parametrize(
    "arguments", [("",), (API_CLIENT_ID,), (API_CLIENT_ID, MCP_CLIENT_ID), (API_CLIENT_ID, "", "x")]
)
def test_adr_impostazioni_entra_fails_without_the_three_arguments(
    installation: EntraInstallation, arguments: tuple[str, ...]
) -> None:
    run = installation.configure(*arguments)

    assert run.status != 0
    assert "Uso:" in run.output
    assert installation.writes == []


def test_adr_impostazioni_entra_refuses_a_name_that_is_an_address(installation: EntraInstallation) -> None:
    run = installation.configure(API_CLIENT_ID, MCP_CLIENT_ID, "https://dev.example.ts.net/mcp")

    assert run.status != 0
    assert "Uso:" in run.output
    assert installation.writes == []


def test_adr_impostazioni_entra_fails_when_az_fails(installation: EntraInstallation) -> None:
    installation.fails = True

    run = installation.configure()

    assert run.status != 0
    assert "non applicate" in run.output
