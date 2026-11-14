from datetime import UTC, datetime
from decimal import Decimal

from autotrading.application.flows.record_cycle_equity import RecordCycleEquityUseCase
from autotrading.domain.flows.account_activity import AccountPosition
from autotrading.domain.flows.cycle_account import CycleAccount
from autotrading.domain.flows.cycle_flow import CycleFlow
from autotrading.domain.flows.equity_snapshot import EquitySnapshot
from autotrading.domain.flows.flow_state import FlowState
from autotrading.domain.flows.statistics_period import TimeWindow
from autotrading.domain.flows.trade_intent import TradeSide
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.equity_snapshots import EquitySnapshotStore, InMemoryEquitySnapshotRepositoryAdapter
from tests.support.flows import a_flow

PLANNED_AT = datetime(2026, 11, 12, 10, 0, tzinfo=UTC)
TENANT = TenantId.new()
FLOW = a_flow(TENANT)
EVERY_CYCLE = TimeWindow(None, None)


def cycle_flow() -> CycleFlow:
    position = AccountPosition("BTC", TradeSide.LONG, Decimal(1), Decimal(20), Decimal(3), 1, Decimal(100))
    state = FlowState(FLOW.id, "USDC", Decimal(300), (position,), Decimal(4), Decimal(1), Decimal(0))
    return CycleFlow(TENANT, FLOW, "test-1", "Hyperliquid", PLANNED_AT, CycleAccount("USDC", Decimal(500), ()), state)


def test_the_cycle_records_the_equity_of_the_state_attributed_to_the_flow() -> None:
    equity = InMemoryEquitySnapshotRepositoryAdapter(EquitySnapshotStore(), TENANT)

    RecordCycleEquityUseCase(equity).execute(FLOW.id.value, PLANNED_AT, cycle_flow())

    assert equity.of_flow(FLOW.id.value, EVERY_CYCLE) == [
        EquitySnapshot(FLOW.id.value, PLANNED_AT, Decimal(300), Decimal(4), Decimal(3), Decimal(1), Decimal(0))
    ]
    assert equity.of_flow(FLOW.id.value, EVERY_CYCLE)[0].equity == Decimal(306)
