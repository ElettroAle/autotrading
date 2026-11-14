from collections.abc import Callable
from datetime import timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from autotrading.adapters.inbound.api.app import HealthReport, create_api
from autotrading.application.tenancy.resolve_tenant import ResolveTenantUseCase
from autotrading.domain.flows.call_cost import CallCost
from autotrading.domain.flows.closed_position import ClosedPosition, CloseReason, PositionEnd
from autotrading.domain.flows.cycle_record import CycleOutcome, CycleRecord
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.trade_intent import TradeSide
from tests.support.flows import a_flow
from tests.support.identity_provider import IdentityProvider
from tests.support.platform import Platform
from tests.support.problems import reason_of

Client = Callable[[str], TestClient]


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


def close(platform: Platform, flow: Flow, net_pnl: str, age: timedelta, fees: str = "0") -> None:
    closed_at = platform.now - age
    platform.closed_positions.positions.append(
        ClosedPosition(
            tenant_id=flow.tenant_id,
            flow_id=flow.id,
            asset="BTC",
            side=TradeSide.LONG,
            leverage=2,
            margin=Decimal(50),
            opening=PositionEnd(Decimal(100), closed_at - timedelta(hours=1)),
            closing=PositionEnd(Decimal(100), closed_at),
            fees=Decimal(fees),
            reason=CloseReason.AGENT,
            realized_pnl=Decimal(net_pnl) + Decimal(fees),
        )
    )


def test_the_statistics_of_a_flow_answer_with_amounts_as_text(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    flow = flow_of(platform, "anna")
    for net_pnl in ("20", "10", "-6", "-4"):
        close(platform, flow, net_pnl, timedelta(days=1), fees="0.75")
    cost = CallCost(10, 10, Decimal("1.20"))
    platform.cycles.record(CycleRecord(flow.id.value, platform.now, CycleOutcome.COMPLETED, cost=cost))

    response = anna.get(f"/flows/{flow.id.value}/statistics")

    assert response.status_code == 200
    assert response.json() == {
        "won": 2,
        "lost": 2,
        "operations": 4,
        "win_rate_percent": "50.00",
        "average_winning_pnl": "15",
        "average_losing_pnl": "-5",
        "total_fees": "3",
        "model_cost_usd": "1.2",
        "model_calls_without_cost": 0,
    }


def test_the_win_rate_has_two_decimals(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    flow = flow_of(platform, "anna")
    for net_pnl in ("1", "1", "-1"):
        close(platform, flow, net_pnl, timedelta(days=1))

    body = anna.get(f"/flows/{flow.id.value}/statistics").json()

    assert body["win_rate_percent"] == "66.67"


def test_without_operations_the_win_rate_and_the_averages_are_null(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    flow = flow_of(platform, "anna")

    body = anna.get(f"/flows/{flow.id.value}/statistics").json()

    assert body["operations"] == 0
    assert (body["win_rate_percent"], body["average_winning_pnl"], body["average_losing_pnl"]) == (None, None, None)


def test_the_period_limits_the_operations(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    flow = flow_of(platform, "anna")
    close(platform, flow, "20", timedelta(days=10))
    close(platform, flow, "-4", timedelta(days=2))

    body = anna.get(f"/flows/{flow.id.value}/statistics", params={"period": "7d"}).json()

    assert (body["won"], body["lost"], body["operations"]) == (0, 1, 1)


def test_a_range_takes_its_days_from_from_and_to(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    flow = flow_of(platform, "anna")
    close(platform, flow, "20", timedelta(days=10))
    close(platform, flow, "-4", timedelta(days=2))
    day = (platform.now - timedelta(days=10)).date().isoformat()

    params = {"period": "range", "from": day, "to": day}
    body = anna.get(f"/flows/{flow.id.value}/statistics", params=params).json()

    assert (body["won"], body["operations"]) == (1, 1)


def test_an_invalid_period_answers_400_with_the_reason(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    flow = flow_of(platform, "anna")

    params = {"period": "range", "from": "2026-11-03", "to": "2026-11-01"}
    response = anna.get(f"/flows/{flow.id.value}/statistics", params=params)

    assert response.status_code == 400
    assert reason_of(response) == {"detail": "periodo non valido: il giorno iniziale è successivo al giorno finale"}


def test_the_statistics_of_a_flow_of_another_user_do_not_exist(client_of: Client, platform: Platform) -> None:
    flow = flow_of(platform, "bruno")

    response = client_of("anna").get(f"/flows/{flow.id.value}/statistics")

    assert response.status_code == 404
    assert reason_of(response) == {"detail": "flusso non trovato"}
