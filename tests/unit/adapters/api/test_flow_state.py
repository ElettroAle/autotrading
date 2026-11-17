from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from autotrading.adapters.inbound.api.app import HealthReport, create_api
from autotrading.adapters.inbound.api.flow_state import FlowStateResponse
from autotrading.application.tenancy.resolve_tenant import ResolveTenantUseCase
from autotrading.domain.flows.balance_comparison import BalanceComparison
from autotrading.domain.flows.capital_change import CapitalChange, CapitalChangeReason
from autotrading.domain.flows.cycle_record import CycleOutcome, CycleRecord
from autotrading.domain.flows.equity_snapshot import EquitySnapshot
from autotrading.domain.flows.exit_plan import ExitPlan
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.flow_results import FlowResults
from autotrading.domain.flows.flow_state import FlowState
from autotrading.domain.flows.ledger import FlowTotals
from autotrading.domain.flows.reconciliation_alarm import ReconciliationAlarm
from tests.support.activity import a_position, an_activity
from tests.support.flows import a_configuration, a_flow, account_id_of
from tests.support.identity_provider import IdentityProvider
from tests.support.platform import Platform
from tests.support.problems import reason_of

Client = Callable[[str], TestClient]
NOW = datetime(2026, 11, 14, 12, 0, tzinfo=UTC)


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
    account_id = account_id_of(platform, user)
    configuration = a_configuration(assets=("BTC",), allocated_capital=Decimal(500))
    flow = a_flow(platform.tenant_of(user), account_id=account_id, configuration=configuration)
    platform.flows.flows.append(flow)
    return flow


def test_the_state_of_a_flow_answers_its_attributed_values(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    flow = flow_of(platform, "anna")
    platform.ledger.totals[flow.id] = FlowTotals(flow.id, Decimal(40), Decimal(2))
    platform.account_activity.activities[flow.assigned_account_id] = an_activity(
        positions=(
            a_position(
                "BTC",
                margin=Decimal(100),
                unrealized_pnl=Decimal(12),
                size=Decimal("0.010"),
                leverage=3,
                entry_price=Decimal("60000.0"),
                mark_price=Decimal("61200.0"),
            ),
            a_position("ETH"),
        ),
    )

    response = anna.get(f"/flows/{flow.id.value}/state")

    assert response.status_code == 200
    assert response.json() == {
        "flow_id": str(flow.id.value),
        "currency": "USDC",
        "allocated_capital": "500",
        "available_liquidity": "438",
        "margin": "100",
        "unrealized_pnl": "12",
        "realized_pnl": "40",
        "fees": "2",
        "total_value": "550",
        "return_percent": "10",
        "positions": [
            {
                "asset": "BTC",
                "side": "long",
                "size": "0.01",
                "leverage": "3",
                "entry_price": "60000",
                "mark_price": "61200",
                "margin": "100",
                "unrealized_pnl": "12",
                "unrealized_pnl_percent": "12",
                "target_price": None,
                "stop_price": None,
                "invalidation": None,
            }
        ],
        "summary": {
            "total_gain": "50",
            "total_gain_percent": "10.00",
            "period_gain": "0",
            "period_gain_percent": "0.00",
            "open_positions": 1,
            "failed_cycles": 0,
        },
        "openings_suspension": None,
    }


def test_the_state_of_a_flow_answers_its_results_in_the_period_asked_for(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    flow = flow_of(platform, "anna")
    platform.account_activity.activities[flow.assigned_account_id] = an_activity()
    platform.now = NOW
    platform.cycles.record(CycleRecord(flow.id.value, NOW - timedelta(days=8), CycleOutcome.FAILED))
    platform.cycles.record(CycleRecord(flow.id.value, NOW - timedelta(days=2), CycleOutcome.FAILED))
    platform.cycles.record(CycleRecord(flow.id.value, NOW - timedelta(days=1), CycleOutcome.FAILED))
    for days_ago, equity in ((8, "490"), (6, "500"), (1, "502")):
        planned_at = NOW - timedelta(days=days_ago)
        platform.equity_snapshots.snapshots[platform.tenant_of("anna"), flow.id.value, planned_at] = EquitySnapshot(
            flow.id.value, planned_at, Decimal(500), Decimal(equity) - Decimal(500), Decimal(0), Decimal(0), Decimal(0)
        )

    summary = anna.get(f"/flows/{flow.id.value}/state?period=7d").json()["summary"]

    assert (summary["period_gain"], summary["period_gain_percent"], summary["failed_cycles"]) == ("2", "0.40", 2)


def test_the_state_of_a_flow_refuses_a_period_the_user_cannot_have_meant(client_of: Client, platform: Platform) -> None:
    flow = flow_of(platform, "anna")

    response = client_of("anna").get(f"/flows/{flow.id.value}/state?period=1y")

    assert (response.status_code, reason_of(response)) == (
        400,
        {"detail": "periodo non valido: scegliere tra 30m, 1h, 12h, 24h, 7d, 30d, all, range"},
    )


def test_a_position_without_margin_answers_no_pnl_percent(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    flow = flow_of(platform, "anna")
    platform.account_activity.activities[flow.assigned_account_id] = an_activity(positions=(a_position("BTC"),))

    [position] = anna.get(f"/flows/{flow.id.value}/state").json()["positions"]

    assert position["unrealized_pnl_percent"] is None


def test_a_position_answers_its_exit_plan_in_force(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    flow = flow_of(platform, "anna")
    platform.account_activity.activities[flow.assigned_account_id] = an_activity(positions=(a_position("BTC"),))
    platform.exit_plans.plans[platform.tenant_of("anna"), flow.id, "BTC"] = ExitPlan(
        Decimal("63000.0"), Decimal(58500), "chiusura a 4 ore sotto 59000"
    )

    [position] = anna.get(f"/flows/{flow.id.value}/state").json()["positions"]

    assert (position["target_price"], position["stop_price"], position["invalidation"]) == (
        "63000",
        "58500",
        "chiusura a 4 ore sotto 59000",
    )


def test_a_flow_of_another_tenant_is_not_found(client_of: Client, platform: Platform) -> None:
    theirs = flow_of(platform, "bruno")

    response = client_of("anna").get(f"/flows/{theirs.id.value}/state")

    assert (response.status_code, reason_of(response)) == (404, {"detail": "flusso non trovato"})


def test_an_exchange_that_cannot_be_read_answers_unavailable(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    flow = flow_of(platform, "anna")
    platform.account_activity.activities[flow.assigned_account_id] = an_activity()
    platform.account_activity.reachable = False

    response = anna.get(f"/flows/{flow.id.value}/state")

    assert (response.status_code, reason_of(response)) == (503, {"detail": "exchange non raggiungibile, riprovare"})


def test_the_return_is_compounded_across_the_changes_of_the_capital(client_of: Client, platform: Platform) -> None:
    # ADR rendimento-composto-tra-le-variazioni-di-capitale: a cash-out at 1100 leaves 10%, then 1050 makes it 15.50%.
    anna = client_of("anna")
    flow = flow_of(platform, "anna")
    capital = flow.configuration.assigned_capital
    platform.account_activity.activities[flow.assigned_account_id] = an_activity()
    platform.ledger.totals[flow.id] = FlowTotals(flow.id, capital * Decimal("0.15"))
    cash_out = CapitalChange(
        flow.id,
        datetime(2026, 11, 16, 10, 0, tzinfo=UTC),
        capital,
        capital,
        platform.user_id_of("anna"),
        CapitalChangeReason.CASH_OUT,
        capital / 10,
        value_before=capital * Decimal("1.1"),
        cashed_profit=capital / 10,
    )
    platform.flows.capital_changes[flow.id] = [cash_out]

    state = anna.get(f"/flows/{flow.id.value}/state").json()

    assert (state["return_percent"], state["summary"]["total_gain_percent"]) == ("15.5", "15.50")


def test_a_state_without_capital_answers_no_return() -> None:
    state = FlowState(FlowId.new(), "USDC", Decimal(0), (), Decimal(5), Decimal(0), Decimal(0))

    assert FlowStateResponse.of(FlowResults(state, Decimal(0), 0)).return_percent is None


def test_the_state_of_a_flow_tells_why_its_openings_are_suspended(client_of: Client, platform: Platform) -> None:
    anna = client_of("anna")
    flow = flow_of(platform, "anna")
    platform.account_activity.activities[flow.assigned_account_id] = an_activity()
    comparison = BalanceComparison(Decimal(1000), Decimal(980), NOW)
    platform.readings.open(ReconciliationAlarm.of(flow.assigned_account_id, comparison))

    state = anna.get(f"/flows/{flow.id.value}/state").json()

    assert state["openings_suspension"] == {
        "reason": "allarme di riconciliazione sul conto test-1",
        "suspended_at": "2026-11-14T12:00:00Z",
        "cause": "riconciliazione",
        "resumable": False,
    }
