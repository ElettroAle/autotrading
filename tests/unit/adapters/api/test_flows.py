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
KEY = "K-OPENROUTER-TEST"


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
        "bring_to_minimum": False,
    }
    assert [(source["name"], source["weight"]) for source in sources] == [("notizie", 7)]


def test_a_flow_can_be_created_bringing_its_openings_to_the_exchange_minimum(
    client_of: Client, platform: Platform
) -> None:
    response = client_of("anna").post("/flows", json=a_request(platform, "anna", bring_to_minimum=True))

    assert response.status_code == 201
    assert response.json()["bring_to_minimum"] is True


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


def test_a_flow_is_modified_compared_commanded_and_archived(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    flow_id = anna.post("/flows", json=a_request(platform, "anna")).json()["id"]

    modified = anna.patch(
        f"/flows/{flow_id}", json={"cycle_minutes": 30, "instructions": "audace", "bring_to_minimum": True}
    )

    assert (modified.status_code, modified.json()["version"], modified.json()["cycle_minutes"]) == (200, 2, 30)
    first = anna.get(f"/flows/{flow_id}/versions/1").json()
    assert (
        first["version"],
        first["cycle_minutes"],
        first["instructions"],
        first["allocated_capital"],
        first["bring_to_minimum"],
    ) == (
        1,
        15,
        "prudente",
        "400",
        False,
    )
    assert anna.get(f"/flows/{flow_id}/versions/1/differences/2").json() == [
        {"part": "intervallo di ciclo", "before": "15 minuti", "after": "30 minuti"},
        {"part": "istruzioni", "before": "prudente", "after": "audace"},
        {"part": "porta al minimo", "before": "no", "after": "sì"},
    ]
    assert [anna.post(f"/flows/{flow_id}/{action}").json()["status"] for action in ("start", "pause", "resume")] == [
        "attivo",
        "in pausa",
        "attivo",
    ]
    refused = anna.post(f"/flows/{flow_id}/archive")
    assert (refused.status_code, reason_of(refused)) == (409, {"detail": "si archivia solo un flusso fermo"})


def test_an_archived_flow_is_listed_apart(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    flow_id = anna.post("/flows", json=a_request(platform, "anna")).json()["id"]

    archived = anna.post(f"/flows/{flow_id}/archive")

    assert (archived.status_code, archived.json()["status"]) == (200, "archiviato")
    assert anna.get("/flows").json() == []
    assert [flow["id"] for flow in anna.get("/flows", params={"archived": True}).json()] == [flow_id]


@pytest.mark.parametrize(
    ("changes", "status", "reason"),
    [
        ({"cycle_minutes": 0}, 422, "intervallo di ciclo fuori da 1-1440 minuti"),
        ({"account_id": str(uuid4())}, 422, "il conto di un flusso non si cambia"),
        ({"assets": ["XYZ"]}, 422, "asset non negoziabile sull'exchange: XYZ"),
        ({"model": "openai/inesistente", "model_parameters": {}}, 422, "modello non disponibile: openai/inesistente"),
        ({"sources": [{"name": "inesistente"}]}, 422, "fonte non disponibile: inesistente"),
        (
            {"max_leverage": 0, "max_margin_exposure_percent": "5", "max_value_exposure_percent": "5"},
            422,
            "limite di rischio non valido: leva massima",
        ),
    ],
)
def test_an_invalid_change_answers_with_the_reason(
    client_of: Client, platform: Platform, changes: dict[str, Any], status: int, reason: str
) -> None:
    anna = client_of("anna")
    flow_id = anna.post("/flows", json=a_request(platform, "anna")).json()["id"]

    response = anna.patch(f"/flows/{flow_id}", json=changes)

    assert (response.status_code, reason_of(response)) == (status, {"detail": reason})
    assert anna.get("/flows").json()[0]["version"] == 1


def test_a_flow_of_another_tenant_or_a_missing_version_is_not_found(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    flow_id = anna.post("/flows", json=a_request(platform, "anna")).json()["id"]
    bruno = client_of("bruno")

    for response in (
        bruno.patch(f"/flows/{flow_id}", json={"instructions": "x"}),
        bruno.post(f"/flows/{flow_id}/start"),
        bruno.post(f"/flows/{flow_id}/archive"),
        bruno.get(f"/flows/{flow_id}/versions/1"),
    ):
        assert (response.status_code, reason_of(response)) == (404, {"detail": "flusso non trovato"})
    missing = anna.get(f"/flows/{flow_id}/versions/1/differences/5")
    assert (missing.status_code, reason_of(missing)) == (404, {"detail": "versione di configurazione non trovata: 5"})
    assert anna.post(f"/flows/{flow_id}/explode").status_code == 422
    refused = anna.post(f"/flows/{flow_id}/pause")
    assert (refused.status_code, reason_of(refused)) == (
        409,
        {"detail": "comando pausa non ammesso per un flusso fermo"},
    )


def test_a_stop_answers_the_flow_stopped_and_the_positions_left_open(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    flow_id = anna.post("/flows", json=a_request(platform, "anna")).json()["id"]
    anna.post(f"/flows/{flow_id}/start")
    hold_position(platform, "anna", ACCOUNT, "BTC")
    hold_position(platform, "anna", ACCOUNT, "ETH")
    platform.order_exchange.closing_rejections["ETH"] = "Order rejected"

    response = anna.post(f"/flows/{flow_id}/stop")

    assert response.status_code == 200
    body = response.json()
    assert (body["flow"]["id"], body["flow"]["status"]) == (flow_id, "fermo")
    assert body["left_open"] == [{"asset": "ETH", "reason": "Order rejected"}]
    refused = anna.post(f"/flows/{flow_id}/stop")
    assert (refused.status_code, reason_of(refused)) == (
        409,
        {"detail": "comando ferma non ammesso per un flusso fermo"},
    )


def test_the_capital_of_a_flow_changes_with_its_history(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    flow_id = anna.post("/flows", json=a_request(platform, "anna")).json()["id"]

    changed = anna.put(f"/flows/{flow_id}/allocated-capital", json={"allocated_capital": "700.50"})

    assert (changed.status_code, changed.json()["allocated_capital"], changed.json()["version"]) == (200, "700.5", 2)
    (change,) = anna.get(f"/flows/{flow_id}/capital-changes").json()
    assert change == {
        "changed_at": platform.now.isoformat().replace("+00:00", "Z"),
        "previous": "400",
        "new": "700.5",
        "user_id": platform.directory.person("anna").object_id,
    }
    refused = anna.put(f"/flows/{flow_id}/allocated-capital", json={"allocated_capital": "1000.51"})
    assert (refused.status_code, reason_of(refused)) == (
        422,
        {"detail": "capitale allocato oltre il capitale disponibile: 1000 USDC"},
    )


def test_stop_and_capital_of_a_flow_of_another_tenant_are_not_found(client_of: Client, platform: Platform) -> None:
    flow_id = client_of("anna").post("/flows", json=a_request(platform, "anna")).json()["id"]
    bruno = client_of("bruno")

    for response in (
        bruno.post(f"/flows/{flow_id}/stop"),
        bruno.put(f"/flows/{flow_id}/allocated-capital", json={"allocated_capital": "10"}),
        bruno.get(f"/flows/{flow_id}/capital-changes"),
    ):
        assert (response.status_code, reason_of(response)) == (404, {"detail": "flusso non trovato"})


def test_an_account_with_an_active_flow_is_removed_only_confirming(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    request = a_request(platform, "anna")
    flow_id = anna.post("/flows", json=request).json()["id"]
    anna.post(f"/flows/{flow_id}/start")

    suspended = anna.delete(f"/accounts/{request['account_id']}")
    removed = anna.delete(f"/accounts/{request['account_id']}", params={"confirmed": True})

    assert (suspended.status_code, reason_of(suspended)) == (
        409,
        {"detail": "il conto ha flussi attivi o in pausa che verranno fermati: alfa"},
    )
    assert removed.status_code == 204
    assert [flow["status"] for flow in anna.get("/flows", params={"archived": True}).json()] == ["archiviato"]
