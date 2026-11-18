"""The routes of the decisions of a flow: the last one (R6.5.4, ADR decisioni-del-ciclo-registrate-per-asset) and the
history (R6.5.5, ADR storico-delle-decisioni-nell-api).
"""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from autotrading.adapters.inbound.api.app import HealthReport, create_api
from autotrading.application.tenancy.resolve_tenant import ResolveTenantUseCase
from autotrading.domain.flows.cycle_record import CycleOutcome, CycleRecord
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.recorded_decision import DecisionAction, RecordedDecision
from autotrading.domain.flows.trade_side import TradeSide
from tests.support.flows import a_flow
from tests.support.identity_provider import IdentityProvider
from tests.support.platform import Platform
from tests.support.problems import reason_of

Client = Callable[[str], TestClient]
TEN = datetime(2026, 11, 16, 10, 0, tzinfo=UTC)


@pytest.fixture
def platform() -> Platform:
    return Platform()


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
        return TestClient(api, headers={"Authorization": f"Bearer {provider.token_for(person)}"})

    return client


def flow_of(platform: Platform, user: str) -> Flow:
    flow = a_flow(platform.tenant_of(user))
    platform.flows.flows.append(flow)
    return flow


def test_the_last_decision_answers_with_its_instant_and_each_asset(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    flow = flow_of(platform, "anna")
    decisions = (
        RecordedDecision("BTC", DecisionAction.OPEN, TradeSide.LONG, 72, "trend rialzista"),
        RecordedDecision("ETH", DecisionAction.HOLD, None, None, "attesa"),
    )
    platform.cycles.record(CycleRecord(flow.id.value, TEN, CycleOutcome.COMPLETED, decisions=decisions))

    response = anna.get(f"/flows/{flow.id.value}/decisions/latest")

    assert response.status_code == 200
    assert response.json() == {
        "planned_at": "2026-11-16T10:00:00Z",
        "decisions": [
            {
                "asset": "BTC",
                "action": "apri",
                "direction": "long",
                "confidence": 72,
                "reasoning": "trend rialzista",
            },
            {"asset": "ETH", "action": "mantieni", "direction": None, "confidence": None, "reasoning": "attesa"},
        ],
    }


def test_a_flow_without_decisions_answers_null(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    flow = flow_of(platform, "anna")

    response = anna.get(f"/flows/{flow.id.value}/decisions/latest")

    assert response.status_code == 200
    assert response.json() is None


def test_the_flow_of_another_tenant_is_not_found(client_of: Client, platform: Platform) -> None:
    flow = flow_of(platform, "bruno")

    response = client_of("anna").get(f"/flows/{flow.id.value}/decisions/latest")

    assert response.status_code == 404
    assert reason_of(response) == {"detail": "flusso non trovato"}


def test_an_unknown_flow_is_not_found(client_of: Client) -> None:
    assert client_of("anna").get(f"/flows/{uuid4()}/decisions/latest").status_code == 404


OPENING = RecordedDecision("BTC", DecisionAction.OPEN, TradeSide.LONG, 72, "trend rialzista")
SHORTING = RecordedDecision("ETH", DecisionAction.OPEN, TradeSide.SHORT, 65, "trend ribassista")
HOLDING = RecordedDecision("ETH", DecisionAction.HOLD, None, None, "attesa")


def record_decisions(platform: Platform, flow: Flow) -> None:
    older = TEN - timedelta(days=10)
    platform.cycles.record(CycleRecord(flow.id.value, older, CycleOutcome.COMPLETED, decisions=(HOLDING,)))
    platform.cycles.record(CycleRecord(flow.id.value, TEN, CycleOutcome.COMPLETED, decisions=(OPENING, SHORTING)))


def test_the_history_answers_a_page_of_decisions_with_the_instant_of_each_cycle(
    client_of: Client, platform: Platform
) -> None:
    anna = client_of("anna")
    flow = flow_of(platform, "anna")
    record_decisions(platform, flow)

    response = anna.get(f"/flows/{flow.id.value}/decisions")

    assert response.status_code == 200
    assert response.json() == {
        "page": 1,
        "has_next": False,
        "total": 3,
        "decisions": [
            {
                "planned_at": "2026-11-16T10:00:00Z",
                "asset": "BTC",
                "action": "apri",
                "direction": "long",
                "confidence": 72,
                "reasoning": "trend rialzista",
            },
            {
                "planned_at": "2026-11-16T10:00:00Z",
                "asset": "ETH",
                "action": "apri",
                "direction": "short",
                "confidence": 65,
                "reasoning": "trend ribassista",
            },
            {
                "planned_at": "2026-11-06T10:00:00Z",
                "asset": "ETH",
                "action": "mantieni",
                "direction": None,
                "confidence": None,
                "reasoning": "attesa",
            },
        ],
    }


def test_the_history_is_filtered_by_asset_action_and_direction(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    flow = flow_of(platform, "anna")
    record_decisions(platform, flow)

    combined = anna.get(
        f"/flows/{flow.id.value}/decisions", params={"asset": "ETH", "action": "apri", "direction": "short"}
    )
    by_direction = anna.get(f"/flows/{flow.id.value}/decisions", params={"direction": "short"})
    by_action = anna.get(f"/flows/{flow.id.value}/decisions", params={"action": "mantieni"})

    assert [(each["asset"], each["direction"]) for each in combined.json()["decisions"]] == [("ETH", "short")]
    assert combined.json()["total"] == 1
    assert [each["direction"] for each in by_direction.json()["decisions"]] == ["short"]
    assert [each["action"] for each in by_action.json()["decisions"]] == ["mantieni"]


def test_the_history_follows_the_period_of_the_page(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    flow = flow_of(platform, "anna")
    record_decisions(platform, flow)

    in_range = anna.get(
        f"/flows/{flow.id.value}/decisions",
        params={"period": "range", "from": "2026-11-06T10:00Z", "to": "2026-11-06T10:00Z"},
    )

    assert [each["planned_at"] for each in in_range.json()["decisions"]] == ["2026-11-06T10:00:00Z"]


def test_the_history_answers_the_page_asked_for(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    flow = flow_of(platform, "anna")
    record_decisions(platform, flow)

    response = anna.get(f"/flows/{flow.id.value}/decisions", params={"page": 2})

    assert (response.json()["page"], response.json()["decisions"], response.json()["total"]) == (2, [], 3)


@pytest.mark.parametrize(
    ("params", "detail"),
    [
        ({"action": "apertura"}, "azione non valida: scegliere tra apri, chiudi, mantieni, aggiorna"),
        ({"direction": "rialzo"}, "direzione non valida: scegliere tra long, short"),
        ({"period": "1d"}, "scegliere tra 30m, 1h, 6h, 12h, 24h, 7d, 30d, all, range"),
        ({"from": "2026-11-06T10:00Z"}, "inizio e fine valgono solo per un intervallo"),
    ],
)
def test_an_unknown_value_of_the_history_is_a_bad_request(
    client_of: Client, platform: Platform, params: dict[str, str], detail: str
) -> None:
    flow = flow_of(platform, "anna")

    response = client_of("anna").get(f"/flows/{flow.id.value}/decisions", params=params)

    assert response.status_code == 400
    assert response.headers["content-type"] == "application/problem+json"
    assert detail in reason_of(response)["detail"]


def test_the_history_of_a_flow_of_another_tenant_is_not_found(client_of: Client, platform: Platform) -> None:
    flow = flow_of(platform, "bruno")
    record_decisions(platform, flow)

    response = client_of("anna").get(f"/flows/{flow.id.value}/decisions")

    assert response.status_code == 404
    assert reason_of(response) == {"detail": "flusso non trovato"}
