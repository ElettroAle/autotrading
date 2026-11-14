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
from autotrading.domain.flows.equity_snapshot import EquitySnapshot
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.trade_intent import TradeSide
from tests.fakes.equity_snapshots import InMemoryEquitySnapshotRepositoryAdapter
from tests.support.flows import a_flow
from tests.support.identity_provider import IdentityProvider
from tests.support.platform import Platform
from tests.support.problems import reason_of

Client = Callable[[str], TestClient]
CYCLE = timedelta(minutes=15)


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


def flow_of(platform: Platform, user: str, name: str, *values: str, age: timedelta = timedelta(days=1)) -> Flow:
    flow = a_flow(platform.tenant_of(user), name=name)
    platform.flows.flows.append(flow)
    equity = InMemoryEquitySnapshotRepositoryAdapter(platform.equity_snapshots, flow.tenant_id)
    zero = Decimal(0)
    for index, value in enumerate(values):
        planned_at = platform.now - age + index * CYCLE
        equity.record(EquitySnapshot(flow.id.value, planned_at, Decimal(value), zero, zero, zero, zero))
    return flow


def close(platform: Platform, flow: Flow, net_pnl: str, fees: str) -> None:
    closed_at = platform.now - timedelta(hours=2)
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


def test_the_ranking_answers_a_row_per_flow_with_numbers_as_text(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    alfa = flow_of(platform, "anna", "alfa", "300", "330", "297", "360")
    close(platform, alfa, "20", "1")
    close(platform, alfa, "-6", "0.5")
    cost = CallCost(10, 10, Decimal("1.20"))
    platform.cycles.record(CycleRecord(alfa.id.value, platform.now, CycleOutcome.COMPLETED, cost=cost))

    response = anna.get("/flows/ranking")

    assert response.status_code == 200
    assert response.json() == [
        {
            "flow_id": str(alfa.id.value),
            "flow_name": "alfa",
            "return_percent": "20.00",
            "max_drawdown_percent": "10.00",
            "pnl": "14",
            "total_fees": "1.5",
            "win_rate_percent": "50.00",
            "operations": 2,
            "model_cost_usd": "1.2",
            "model_calls_without_cost": 0,
        }
    ]


def test_the_rows_go_from_the_highest_return(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    flow_of(platform, "anna", "beta", "200", "210")
    flow_of(platform, "anna", "alfa", "300", "360")

    body = anna.get("/flows/ranking").json()

    assert [row["flow_name"] for row in body] == ["alfa", "beta"]


def test_what_is_not_available_is_null(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    flow_of(platform, "anna", "alfa", "0", "10")

    (row,) = anna.get("/flows/ranking").json()

    assert (row["return_percent"], row["win_rate_percent"], row["operations"]) == (None, None, 0)


def test_the_period_leaves_out_the_flows_without_cycles_in_it(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    flow_of(platform, "anna", "alfa", "100", "110")
    flow_of(platform, "anna", "gamma", "100", "500", age=timedelta(days=20))

    body = anna.get("/flows/ranking", params={"period": "7d"}).json()

    assert [row["flow_name"] for row in body] == ["alfa"]


def test_a_range_takes_its_days_from_from_and_to(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    flow_of(platform, "anna", "alfa", "100", "110", age=timedelta(days=20))
    flow_of(platform, "anna", "beta", "100", "120")
    day = (platform.now - timedelta(days=20)).date().isoformat()

    body = anna.get("/flows/ranking", params={"period": "range", "from": day, "to": day}).json()

    assert [row["flow_name"] for row in body] == ["alfa"]


def test_an_invalid_period_answers_400_with_the_reason(client_of: Client) -> None:
    params = {"period": "range", "from": "2026-11-03", "to": "2026-11-01"}

    response = client_of("anna").get("/flows/ranking", params=params)

    assert response.status_code == 400
    assert reason_of(response) == {"detail": "periodo non valido: il giorno iniziale è successivo al giorno finale"}


def test_the_ranking_shows_only_the_flows_of_the_user(client_of: Client, platform: Platform) -> None:
    flow_of(platform, "bruno", "omega", "100", "400")

    assert client_of("anna").get("/flows/ranking").json() == []
