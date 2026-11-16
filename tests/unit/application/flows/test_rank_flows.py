from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from autotrading.application.flows.rank_flows import RankFlowsCommand, RankFlowsUseCase
from autotrading.domain.flows.call_cost import CallCost
from autotrading.domain.flows.capital_change import CapitalChange, CapitalChangeReason
from autotrading.domain.flows.closed_position import ClosedPosition, CloseReason, PositionEnd
from autotrading.domain.flows.cycle_record import CycleOutcome, CycleRecord
from autotrading.domain.flows.equity_snapshot import EquitySnapshot
from autotrading.domain.flows.errors import InvalidStatisticsPeriodError
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_ranking import FlowRanking
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.flows.trade_side import TradeSide
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId
from tests.fakes.closed_position_repository import ClosedPositionStore, InMemoryClosedPositionRepositoryAdapter
from tests.fakes.cycles import InMemoryCycleHistoryAdapter, InMemoryCycleRepositoryAdapter
from tests.fakes.equity_snapshots import EquitySnapshotStore, InMemoryEquitySnapshotRepositoryAdapter
from tests.fakes.flow_repository import FlowStore, InMemoryFlowRepositoryAdapter
from tests.support.flows import a_flow

NOW = datetime(2026, 11, 14, 12, tzinfo=UTC)
RECENT = NOW - timedelta(days=1)
LONG_AGO = NOW - timedelta(days=20)
CYCLE = timedelta(minutes=15)
TENANT = TenantId.new()


class Platform:
    def __init__(self) -> None:
        self.flows = FlowStore()
        self.equity = EquitySnapshotStore()
        self.positions = ClosedPositionStore()
        self.cycles = InMemoryCycleRepositoryAdapter()

    def flow(
        self,
        name: str,
        *values: str,
        since: datetime = RECENT,
        tenant_id: TenantId = TENANT,
        status: FlowStatus = FlowStatus.ACTIVE,
    ) -> Flow:
        flow = a_flow(tenant_id, name=name, status=status)
        self.flows.flows.append(flow)
        equity = InMemoryEquitySnapshotRepositoryAdapter(self.equity, tenant_id)
        zero = Decimal(0)
        for index, value in enumerate(values):
            equity.record(EquitySnapshot(flow.id.value, since + index * CYCLE, Decimal(value), zero, zero, zero, zero))
        return flow

    def close(self, flow: Flow, net_pnl: str, closed_at: datetime, fees: str = "0") -> None:
        self.positions.positions.append(
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

    def call_model(self, flow: Flow, cost: str, planned_at: datetime) -> None:
        call = CallCost(10, 10, Decimal(cost))
        self.cycles.record(CycleRecord(flow.id.value, planned_at, CycleOutcome.COMPLETED, cost=call))

    def use_case(self) -> RankFlowsUseCase:
        return RankFlowsUseCase(
            InMemoryFlowRepositoryAdapter(self.flows, TENANT),
            InMemoryEquitySnapshotRepositoryAdapter(self.equity, TENANT),
            InMemoryClosedPositionRepositoryAdapter(self.positions, TENANT),
            InMemoryCycleHistoryAdapter(self.cycles, self.flows, TENANT),
            lambda: NOW,
        )


@pytest.fixture
def platform() -> Platform:
    return Platform()


def names(rows: tuple[FlowRanking, ...]) -> list[str]:
    return [row.flow_name for row in rows]


def test_the_ranking_goes_from_the_highest_return_of_the_whole_life(platform: Platform) -> None:
    platform.flow("beta", "200", "210")
    platform.flow("alfa", "300", "330", "297", "360")

    rows = platform.use_case().execute(RankFlowsCommand())

    assert names(rows) == ["alfa", "beta"]
    assert (rows[0].return_percent, rows[0].max_drawdown_percent) == (Decimal(20), Decimal(10))


def test_the_return_of_a_flow_is_compounded_across_the_changes_of_its_capital(platform: Platform) -> None:
    # ADR rendimento-composto-tra-le-variazioni-di-capitale: an increase of 900 at 1100, then 2100.
    flow = platform.flow("alfa", "1000", "1100", "2100")
    increase = CapitalChange(
        flow.id,
        RECENT + CYCLE + CYCLE / 2,
        Decimal(1000),
        Decimal(1900),
        UserId("anna"),
        CapitalChangeReason.INCREASE,
        Decimal(900),
        value_before=Decimal(1100),
    )
    platform.flows.capital_changes[flow.id] = [increase]

    (row,) = platform.use_case().execute(RankFlowsCommand())

    assert row.return_percent == Decimal("15.50")


def test_the_ranking_leaves_out_the_archived_flows(platform: Platform) -> None:
    platform.flow("alfa", "100", "110")
    platform.flow("vecchio", "100", "300", status=FlowStatus.ARCHIVED)

    assert names(platform.use_case().execute(RankFlowsCommand())) == ["alfa"]


def test_the_ranking_leaves_out_the_drafts(platform: Platform) -> None:
    platform.flow("alfa", "100", "110")
    platform.flow("bozza", "100", "300", status=FlowStatus.DRAFT)

    assert names(platform.use_case().execute(RankFlowsCommand())) == ["alfa"]


def test_the_ranking_leaves_out_the_flows_of_another_tenant(platform: Platform) -> None:
    platform.flow("alfa", "100", "110")
    platform.flow("omega", "100", "400", tenant_id=TenantId.new())

    assert names(platform.use_case().execute(RankFlowsCommand())) == ["alfa"]


def test_the_ranking_of_a_period_leaves_out_the_flows_without_cycles_in_it(platform: Platform) -> None:
    platform.flow("alfa", "100", "110")
    platform.flow("gamma", "100", "500", since=LONG_AGO)

    assert names(platform.use_case().execute(RankFlowsCommand("7d"))) == ["alfa"]


def test_the_return_and_the_drawdown_of_a_period_use_only_its_cycles(platform: Platform) -> None:
    alfa = platform.flow("alfa", "300", "330", since=LONG_AGO)
    equity = InMemoryEquitySnapshotRepositoryAdapter(platform.equity, TENANT)
    zero = Decimal(0)
    for index, value in enumerate(("297", "360")):
        equity.record(EquitySnapshot(alfa.id.value, RECENT + index * CYCLE, Decimal(value), zero, zero, zero, zero))

    (row,) = platform.use_case().execute(RankFlowsCommand("7d"))

    assert row.return_percent is not None
    assert row.return_percent.quantize(Decimal("0.01")) == Decimal("21.21")
    assert row.max_drawdown_percent == Decimal(0)


def test_the_statistics_of_a_row_are_those_of_the_period(platform: Platform) -> None:
    alfa = platform.flow("alfa", "100", "110")
    platform.close(alfa, "20", RECENT, fees="1")
    platform.close(alfa, "-6", RECENT, fees="0.5")
    platform.close(alfa, "50", LONG_AGO)
    platform.call_model(alfa, "1.20", RECENT)
    platform.call_model(alfa, "3", LONG_AGO)

    (row,) = platform.use_case().execute(RankFlowsCommand("7d"))

    statistics = row.statistics
    assert (statistics.net_pnl, statistics.total_fees, statistics.operations) == (Decimal(14), Decimal("1.5"), 2)
    assert (statistics.win_rate_percent, statistics.model_cost_usd) == (Decimal(50), Decimal("1.20"))


def test_the_ranking_of_a_range_reads_its_days(platform: Platform) -> None:
    platform.flow("alfa", "100", "110", since=LONG_AGO)
    platform.flow("beta", "100", "120")
    rows = platform.use_case().execute(RankFlowsCommand("range", LONG_AGO, LONG_AGO))

    assert names(rows) == ["alfa"]


def test_an_invalid_period_is_refused(platform: Platform) -> None:
    with pytest.raises(InvalidStatisticsPeriodError):
        platform.use_case().execute(
            RankFlowsCommand("range", datetime(2026, 11, 3, 10, tzinfo=UTC), datetime(2026, 11, 3, 9, tzinfo=UTC))
        )


def test_the_ranking_is_empty_without_flows(platform: Platform) -> None:
    assert platform.use_case().execute(RankFlowsCommand()) == ()
