from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient

from autotrading.adapters.inbound.api.app import HealthReport, create_api
from autotrading.application.tenancy.resolve_tenant import ResolveTenantUseCase
from tests.support.flows import OPENROUTER_MODEL, account_id_of, scenario_catalog
from tests.support.identity_provider import IdentityProvider
from tests.support.platform import Platform
from tests.support.problems import reason_of

Client = Callable[[str], TestClient]


@pytest.fixture
def platform() -> Platform:
    platform = Platform()
    platform.model_catalog = scenario_catalog()
    return platform


@pytest.fixture
def client_of(platform: Platform) -> Client:
    provider = IdentityProvider()
    api = create_api(
        HealthReport("1.0.0", "dev"),
        ResolveTenantUseCase(platform.tenants),
        platform.for_tenant,
        provider.authentication(),
    )

    def client(user: str) -> TestClient:
        person = platform.directory.person(user)
        person.roles.add("Utente")
        client = TestClient(api, headers={"Authorization": f"Bearer {provider.token_for(person)}"})
        client.post("/provider-keys", json={"provider": "openrouter", "key": {"api_key": "K-OPENROUTER-TEST"}})
        return client

    return client


def an_original(client: TestClient, platform: Platform, user: str) -> dict[str, Any]:
    request = {
        "name": "alfa",
        "account_id": str(account_id_of(platform, user)),
        "assets": ["BTC"],
        "model": OPENROUTER_MODEL,
        "sources": [{"name": "notizie", "weight": 2}],
        "max_leverage": 5,
        "max_margin_exposure_percent": "10",
        "allocated_capital": "100",
    }
    response = client.post("/flows", json=request)
    assert response.status_code == 201
    created: dict[str, Any] = response.json()
    return created


def test_a_duplicated_flow_answers_as_a_draft_with_account_and_capital_without_assets(
    client_of: Client, platform: Platform
) -> None:
    anna = client_of("anna")
    original = an_original(anna, platform, "anna")

    response = anna.post(f"/flows/{original['id']}/duplicate")

    assert response.status_code == 201
    copy = response.json()
    assert copy["id"] != original["id"]
    assert {key: copy[key] for key in ("name", "account_id", "status", "version", "assets", "allocated_capital")} == {
        "name": "alfa (copia)",
        "account_id": original["account_id"],
        "status": "bozza",
        "version": 1,
        "assets": [],
        "allocated_capital": "100",
    }
    assert (copy["model"], copy["sources"], copy["risk_limits"]) == (
        original["model"],
        original["sources"],
        original["risk_limits"],
    )
    assert [flow["name"] for flow in anna.get("/flows").json()] == ["alfa", "alfa (copia)"]


def test_a_flow_of_another_tenant_is_not_duplicated(client_of: Client, platform: Platform) -> None:
    original = an_original(client_of("anna"), platform, "anna")

    response = client_of("bruno").post(f"/flows/{original['id']}/duplicate")

    assert (response.status_code, reason_of(response)) == (404, {"detail": "flusso non trovato"})


def test_a_draft_configured_in_the_editor_answers_with_account_capital_and_assets_and_then_starts(
    client_of: Client, platform: Platform
) -> None:
    anna = client_of("anna")
    copy = anna.post(f"/flows/{an_original(anna, platform, 'anna')['id']}/duplicate").json()
    account_id = str(account_id_of(platform, "anna", "secondario"))

    configured = anna.patch(
        f"/flows/{copy['id']}",
        json={"account_id": account_id, "allocated_capital": "200", "assets": ["btc"]},
    )
    started = anna.post(f"/flows/{copy['id']}/start")

    assert configured.status_code == 200
    assert {
        key: configured.json()[key] for key in ("account_id", "status", "version", "assets", "allocated_capital")
    } == {
        "account_id": account_id,
        "status": "bozza",
        "version": 2,
        "assets": ["BTC"],
        "allocated_capital": "200",
    }
    assert (started.status_code, started.json()["status"]) == (200, "attivo")


def test_a_copy_started_without_assets_answers_with_what_is_missing(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    copy = anna.post(f"/flows/{an_original(anna, platform, 'anna')['id']}/duplicate").json()

    response = anna.post(f"/flows/{copy['id']}/start")

    assert (response.status_code, reason_of(response)) == (409, {"detail": "asset mancante"})


def test_the_assignment_has_no_route_of_its_own(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    copy = anna.post(f"/flows/{an_original(anna, platform, 'anna')['id']}/duplicate").json()

    response = anna.put(
        f"/flows/{copy['id']}/assignment",
        json={"account_id": copy["account_id"], "allocated_capital": "50", "assets": ["ETH"]},
    )

    assert response.status_code == 405


def test_the_capital_of_a_flow_out_of_draft_answers_with_the_command_of_the_capital(
    client_of: Client, platform: Platform
) -> None:
    anna = client_of("anna")
    original = an_original(anna, platform, "anna")

    response = anna.patch(f"/flows/{original['id']}", json={"allocated_capital": "50"})

    assert (response.status_code, reason_of(response)) == (
        422,
        {
            "detail": "il capitale allocato di un flusso avviato si cambia con il comando del capitale",
            "field": "allocated_capital",
        },
    )


def test_a_new_name_answers_with_the_flow_renamed_at_the_same_version(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    original = an_original(anna, platform, "anna")

    response = anna.patch(f"/flows/{original['id']}", json={"name": "beta"})

    assert response.status_code == 200
    assert (response.json()["name"], response.json()["version"]) == ("beta", 1)
    assert [flow["name"] for flow in anna.get("/flows").json()] == ["beta"]


def test_the_name_of_another_flow_answers_with_the_reason(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    original = an_original(anna, platform, "anna")
    copy = anna.post(f"/flows/{original['id']}/duplicate").json()

    response = anna.patch(f"/flows/{copy['id']}", json={"name": "alfa"})

    assert (response.status_code, reason_of(response)) == (
        409,
        {"detail": "nome già usato da un altro flusso", "field": "name"},
    )


def test_a_partial_draft_answers_with_what_it_lacks_to_start(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    copy = anna.post(f"/flows/{an_original(anna, platform, 'anna')['id']}/duplicate").json()

    listed = {flow["name"]: flow["missing"] for flow in anna.get("/flows").json()}

    assert copy["missing"] == ["asset"]
    assert listed["alfa (copia)"] == ["asset"]


def test_a_complete_draft_answers_with_nothing_missing(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    copy = anna.post(f"/flows/{an_original(anna, platform, 'anna')['id']}/duplicate").json()

    configured = anna.patch(f"/flows/{copy['id']}", json={"assets": ["ETH"]})

    assert (configured.json()["status"], configured.json()["missing"]) == ("bozza", [])


def test_a_flow_out_of_draft_answers_with_nothing_missing(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")

    original = an_original(anna, platform, "anna")

    assert (original["status"], original["missing"]) == ("fermo", [])
