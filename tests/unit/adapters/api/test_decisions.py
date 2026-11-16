"""The route of the last decision of a flow (R6.5.4, ADR decisioni-del-ciclo-registrate-per-asset)."""

from collections.abc import Callable
from datetime import UTC, datetime
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
