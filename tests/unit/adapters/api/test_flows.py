from collections.abc import Callable
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from autotrading.adapters.inbound.api.app import Authentication, HealthReport, create_api
from autotrading.adapters.inbound.api.authentication import AccessTokenVerifier, OidcSigningKeys
from autotrading.application.tenancy.resolve_tenant import ResolveTenantUseCase
from tests.support.flows import OPENROUTER_MODEL, account_id_of, scenario_catalog
from tests.support.identity_provider import SETTINGS, IdentityProvider
from tests.support.platform import Platform
from tests.support.problems import reason_of

Client = Callable[[str], TestClient]
KEY = "K-OPENROUTER-TEST"


@pytest.fixture
def platform() -> Platform:
    platform = Platform()
    platform.model_catalog = scenario_catalog()
    platform.providers.accept("openrouter", KEY)
    return platform


@pytest.fixture
def client_of(platform: Platform) -> Client:
    provider = IdentityProvider()
    verifier = AccessTokenVerifier(SETTINGS, OidcSigningKeys(SETTINGS.discovery_url, provider.fetch))
    api = create_api(
        HealthReport("1.0.0", "dev"),
        ResolveTenantUseCase(platform.tenants),
        platform.for_tenant,
        Authentication(SETTINGS, verifier),
    )

    def client(user: str) -> TestClient:
        person = platform.directory.person(user)
        person.roles.add("Utente")
        client = TestClient(api, headers={"Authorization": f"Bearer {provider.token_for(person)}"})
        client.post("/provider-keys", json={"provider": "openrouter", "key": KEY})
        return client

    return client


def a_request(platform: Platform, user: str, **changes: Any) -> dict[str, Any]:
    return {
        "name": "alfa",
        "account_id": str(account_id_of(platform, user)),
        "assets": ["BTC", "eth"],
        "model": OPENROUTER_MODEL,
        "model_parameters": {"temperature": "0.5"},
        "sources": [{"name": "notizie", "weight": 7}],
        "instructions": "prudente",
        "max_leverage": 5,
        "max_margin_exposure_percent": "10",
        "allocated_capital": "400.00",
        **changes,
    }


def test_a_created_flow_answers_stopped_with_its_whole_configuration(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    request = a_request(platform, "anna")

    response = anna.post("/flows", json=request)

    assert response.status_code == 201
    body = response.json()
    assert body.pop("id")
    sources = body.pop("sources")
    assert body == {
        "name": "alfa",
        "account_id": request["account_id"],
        "status": "fermo",
        "version": 1,
        "assets": ["BTC", "ETH"],
        "cycle_minutes": 15,
        "model": {"name": OPENROUTER_MODEL, "parameters": {"temperature": "0.5"}},
        "instructions": "prudente",
        "risk_limits": {"max_leverage": 5, "max_margin_exposure_percent": "10", "max_value_exposure_percent": None},
        "allocated_capital": "400",
    }
    assert [(source["name"], source["weight"]) for source in sources] == [("notizie", 7)]


def test_the_flows_of_the_tenant_are_listed_and_the_free_capital_shrinks(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    created = anna.post("/flows", json=a_request(platform, "anna")).json()
    account_id = created["account_id"]

    assert [flow["id"] for flow in anna.get("/flows").json()] == [created["id"]]
    assert anna.get(f"/accounts/{account_id}/free-capital").json() == {"amount": "600", "currency": "USDC"}
    assert client_of("bruno").get("/flows").json() == []


@pytest.mark.parametrize(
    ("changes", "status", "reason"),
    [
        ({"name": ""}, 422, "nome del flusso obbligatorio"),
        ({"model": "openai/inesistente"}, 422, "modello non disponibile: openai/inesistente"),
        ({"model_parameters": {"temperature": 3}}, 422, "parametro fuori dai valori ammessi: temperatura"),
        ({"assets": ["XYZ"]}, 422, "asset non negoziabile sull'exchange: XYZ"),
        ({"max_leverage": None}, 422, "la leva massima è obbligatoria"),
        ({"allocated_capital": "1000.01"}, 422, "capitale allocato oltre il capitale libero: 1000 USDC"),
        ({"account_id": str(uuid4())}, 404, "conto non trovato"),
    ],
)
def test_an_invalid_configuration_answers_with_the_reason(
    client_of: Client, platform: Platform, changes: dict[str, Any], status: int, reason: str
) -> None:
    anna = client_of("anna")

    response = anna.post("/flows", json=a_request(platform, "anna", **changes))

    assert (response.status_code, reason_of(response)) == (status, {"detail": reason})
    assert anna.get("/flows").json() == []


def test_a_name_already_used_is_a_conflict(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    anna.post("/flows", json=a_request(platform, "anna", allocated_capital="10"))

    response = anna.post("/flows", json=a_request(platform, "anna", allocated_capital="10"))

    assert (response.status_code, reason_of(response)) == (409, {"detail": "nome già usato da un altro flusso"})


def test_the_free_capital_of_an_account_of_another_tenant_is_not_found(client_of: Client, platform: Platform) -> None:
    client_of("anna")
    account_id = account_id_of(platform, "anna")

    response = client_of("bruno").get(f"/accounts/{account_id}/free-capital")

    assert (response.status_code, reason_of(response)) == (404, {"detail": "conto non trovato"})
