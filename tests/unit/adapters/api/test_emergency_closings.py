from collections.abc import Callable
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from autotrading.adapters.inbound.api.app import HealthReport, create_api
from autotrading.application.tenancy.resolve_tenant import ResolveTenantUseCase
from tests.support.flows import ACCOUNT, OPENROUTER_MODEL, account_id_of, scenario_catalog
from tests.support.identity_provider import IdentityProvider
from tests.support.lifecycle_steps import hold_position
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


def active_flow(client: TestClient, platform: Platform, user: str, name: str, assets: list[str]) -> str:
    request: dict[str, Any] = {
        "name": name,
        "account_id": str(account_id_of(platform, user)),
        "assets": assets,
        "model": OPENROUTER_MODEL,
        "max_leverage": 5,
        "max_margin_exposure_percent": "10",
        "allocated_capital": "100",
    }
    flow_id: str = client.post("/flows", json=request).json()["id"]
    client.post(f"/flows/{flow_id}/start")
    return flow_id


def test_the_closing_of_an_account_answers_the_outcome_of_each_flow(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    alfa = active_flow(anna, platform, "anna", "alfa", ["BTC"])
    beta = active_flow(anna, platform, "anna", "beta", ["ETH"])
    hold_position(platform, "anna", ACCOUNT, "BTC")
    hold_position(platform, "anna", ACCOUNT, "ETH")
    platform.order_exchange.closing_rejections["ETH"] = "Order rejected"
    account_id = str(account_id_of(platform, "anna"))

    response = anna.post("/flows/emergency-closings", json={"account_id": account_id})

    assert response.status_code == 200
    body = response.json()
    assert body["closed_at"] == platform.now.isoformat().replace("+00:00", "Z")
    assert body["scope"] == {"kind": "account", "flow_id": None, "account_id": account_id}
    assert body["flows"] == [
        {"flow_id": alfa, "flow_name": "alfa", "closed": ["BTC"], "left_open": [], "failure": None, "remark": None},
        {
            "flow_id": beta,
            "flow_name": "beta",
            "closed": [],
            "left_open": [{"asset": "ETH", "reason": "Order rejected"}],
            "failure": None,
            "remark": None,
        },
    ]
    statuses = {flow["id"]: flow["status"] for flow in anna.get("/flows").json()}
    assert statuses == {alfa: "in pausa", beta: "in pausa"}


def test_without_a_scope_every_flow_closes(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    alfa = active_flow(anna, platform, "anna", "alfa", ["BTC"])

    response = anna.post("/flows/emergency-closings", json={})

    assert response.status_code == 200
    assert response.json()["scope"] == {"kind": "all", "flow_id": None, "account_id": None}
    (outcome,) = response.json()["flows"]
    assert (outcome["flow_id"], outcome["remark"]) == (alfa, "nessuna posizione da chiudere")


def test_the_preview_counts_the_flows_and_positions_of_the_scope(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    alfa = active_flow(anna, platform, "anna", "alfa", ["BTC"])
    active_flow(anna, platform, "anna", "beta", ["ETH"])
    hold_position(platform, "anna", ACCOUNT, "BTC")

    of_flow = anna.get("/flows/emergency-closings/preview", params={"flow_id": alfa})
    of_all = anna.get("/flows/emergency-closings/preview")

    assert (of_flow.status_code, of_flow.json()) == (200, {"flows": 1, "positions": 1})
    assert of_all.json() == {"flows": 2, "positions": 1}
    assert len(platform.order_exchange.sent) == 0


def test_a_flow_and_an_account_together_are_refused(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    scope = {"flow_id": str(uuid4()), "account_id": str(account_id_of(platform, "anna"))}

    for response in (
        anna.post("/flows/emergency-closings", json=scope),
        anna.get("/flows/emergency-closings/preview", params=scope),
    ):
        assert (response.status_code, reason_of(response)) == (
            400,
            {"detail": "indicare un flusso o un conto, non entrambi"},
        )


def test_a_flow_or_an_account_of_another_tenant_is_not_found(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    flow_id = active_flow(anna, platform, "anna", "alfa", ["BTC"])
    account_id = str(account_id_of(platform, "anna"))
    bruno = client_of("bruno")

    assert reason_of(bruno.post("/flows/emergency-closings", json={"flow_id": flow_id})) == {
        "detail": "flusso non trovato"
    }
    refused = bruno.get("/flows/emergency-closings/preview", params={"account_id": account_id})
    assert (refused.status_code, reason_of(refused)) == (404, {"detail": "conto non trovato"})
