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
        client.post("/provider-keys", json={"provider": "openrouter", "key": "K-OPENROUTER-TEST"})
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


def test_a_duplicated_flow_answers_as_a_draft_without_account_capital_or_assets(
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
        "account_id": None,
        "status": "bozza",
        "version": 1,
        "assets": [],
        "allocated_capital": None,
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


def test_an_assigned_draft_answers_with_account_capital_and_assets_and_then_starts(
    client_of: Client, platform: Platform
) -> None:
    anna = client_of("anna")
    copy = anna.post(f"/flows/{an_original(anna, platform, 'anna')['id']}/duplicate").json()
    account_id = str(account_id_of(platform, "anna", "secondario"))

    assigned = anna.put(
        f"/flows/{copy['id']}/assignment",
        json={"account_id": account_id, "allocated_capital": "200", "assets": ["btc"]},
    )
    started = anna.post(f"/flows/{copy['id']}/start")

    assert assigned.status_code == 200
    assert {
        key: assigned.json()[key] for key in ("account_id", "status", "version", "assets", "allocated_capital")
    } == {
        "account_id": account_id,
        "status": "bozza",
        "version": 2,
        "assets": ["BTC"],
        "allocated_capital": "200",
    }
    assert (started.status_code, started.json()["status"]) == (200, "attivo")


def test_a_draft_started_without_assignment_answers_with_what_is_missing(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    copy = anna.post(f"/flows/{an_original(anna, platform, 'anna')['id']}/duplicate").json()

    response = anna.post(f"/flows/{copy['id']}/start")

    assert (response.status_code, reason_of(response)) == (409, {"detail": "conto, capitale allocato e asset mancanti"})


def test_an_assignment_without_assets_answers_with_the_reason(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    copy = anna.post(f"/flows/{an_original(anna, platform, 'anna')['id']}/duplicate").json()

    response = anna.put(
        f"/flows/{copy['id']}/assignment",
        json={"account_id": str(account_id_of(platform, "anna")), "allocated_capital": "200"},
    )

    assert (response.status_code, reason_of(response)) == (
        422,
        {"detail": "almeno un asset è obbligatorio", "field": "assets"},
    )


def test_a_flow_out_of_draft_is_not_assigned(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    original = an_original(anna, platform, "anna")

    response = anna.put(
        f"/flows/{original['id']}/assignment",
        json={"account_id": original["account_id"], "allocated_capital": "50", "assets": ["ETH"]},
    )

    assert (response.status_code, reason_of(response)) == (
        409,
        {"detail": "conto, capitale e asset si assegnano solo a un flusso in bozza"},
    )
