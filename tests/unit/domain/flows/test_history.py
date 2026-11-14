from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from autotrading.domain.flows.closed_position import ClosedPosition, CloseReason, PositionEnd
from autotrading.domain.flows.cycle_record import CycleOutcome, CycleRecord
from autotrading.domain.flows.errors import VersionWithoutFlowError
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.history import (
    HISTORY_PAGE_SIZE,
    ClosedPositionHistoryEntry,
    CycleHistoryEntry,
    HistoryCursor,
    HistoryFilter,
    HistoryPage,
    HistoryQuery,
    OrderExecution,
    OrderHistoryEntry,
)
from autotrading.domain.flows.statistics_period import StatisticsPeriod, TimeWindow
from autotrading.domain.flows.trade_intent import TradeSide
from autotrading.domain.tenancy.tenant_id import TenantId

NOW = datetime(2026, 11, 30, 12, 0, tzinfo=UTC)
FLOW = uuid4()


def a_cycle_entry(planned_at: datetime, flow_id: UUID = FLOW) -> CycleHistoryEntry:
    return CycleHistoryEntry("alfa", 1, CycleRecord(flow_id, planned_at, CycleOutcome.COMPLETED))


def a_position_entry(closed_at: datetime) -> ClosedPositionHistoryEntry:
    position = ClosedPosition(
        tenant_id=TenantId(uuid4()),
        flow_id=FlowId(FLOW),
        asset="ETH",
        side=TradeSide.LONG,
        leverage=2,
        margin=Decimal(100),
        opening=PositionEnd(Decimal(3000), closed_at - timedelta(hours=1)),
        closing=PositionEnd(Decimal(3100), closed_at),
        fees=Decimal("0.5"),
        reason=CloseReason.AGENT,
    )
    return ClosedPositionHistoryEntry(uuid4(), "alfa", position)


def an_order_entry(created_at: datetime) -> OrderHistoryEntry:
    execution = OrderExecution(created_at, Decimal(100), Decimal("0.1"), Decimal("0.01"))
    return OrderHistoryEntry(
        order_id=uuid4(),
        created_at=created_at,
        account_id=uuid4(),
        account_name="principale",
        flow_id=FLOW,
        flow_name="alfa",
        asset="BTC",
        direction="long",
        closing=False,
        leverage=2,
        requested_size=Decimal("0.1"),
        status="eseguito",
        origin="flusso",
        executions=(execution,),
    )


def test_a_filter_without_values_admits_every_row() -> None:
    criteria = HistoryFilter()

    assert (criteria.flow_id, criteria.account_id, criteria.asset, criteria.version) == (None, None, None, None)
    assert criteria.period == StatisticsPeriod.named("all")


def test_rejects_a_version_without_a_flow() -> None:
    with pytest.raises(VersionWithoutFlowError) as raised:
        HistoryFilter(version=2)

    assert str(raised.value) == "la versione richiede un flusso"
    assert raised.value.status_code == 400


def test_accepts_a_version_of_a_flow() -> None:
    assert HistoryFilter(flow_id=FLOW, version=2).version == 2


def test_the_query_reads_the_window_of_the_period_at_the_given_instant() -> None:
    period = StatisticsPeriod.named("range", date(2026, 11, 10), date(2026, 11, 20))

    query = HistoryQuery.of(HistoryFilter(period=period), NOW, None)

    assert query.window == TimeWindow(datetime(2026, 11, 10, tzinfo=UTC), datetime(2026, 11, 21, tzinfo=UTC))
    assert query.limit == HISTORY_PAGE_SIZE == 50
    assert query.after is None


def test_the_query_keeps_where_the_page_starts() -> None:
    after = HistoryCursor(NOW, FLOW)

    assert HistoryQuery.of(HistoryFilter(), NOW, after).after == after


def test_the_cursor_of_a_cycle_is_its_planned_instant_and_its_flow() -> None:
    assert a_cycle_entry(NOW).cursor == HistoryCursor(NOW, FLOW)


def test_the_cursor_of_a_closed_position_is_its_closing_instant_and_its_identifier() -> None:
    entry = a_position_entry(NOW)

    assert entry.cursor == HistoryCursor(NOW, entry.position_id)


def test_the_cursor_of_an_order_is_its_creation_instant_and_its_identifier() -> None:
    entry = an_order_entry(NOW)

    assert entry.cursor == HistoryCursor(NOW, entry.order_id)


def test_a_cursor_orders_by_instant_then_by_key() -> None:
    low, high = UUID(int=1), UUID(int=2)

    assert HistoryCursor(NOW, high) < HistoryCursor(NOW + timedelta(seconds=1), low)
    assert HistoryCursor(NOW, low) < HistoryCursor(NOW, high)


def test_a_page_with_one_row_more_than_the_limit_says_where_the_next_starts() -> None:
    rows = [a_cycle_entry(NOW - timedelta(minutes=minute)) for minute in range(4)]

    page = HistoryPage.of(rows, 3)

    assert page.entries == tuple(rows[:3])
    assert page.next == rows[2].cursor


def test_the_last_page_has_no_next() -> None:
    rows = [an_order_entry(NOW - timedelta(minutes=minute)) for minute in range(3)]

    page = HistoryPage.of(rows, 3)

    assert page.entries == tuple(rows)
    assert page.next is None


def test_an_empty_page_has_no_next() -> None:
    page: HistoryPage[ClosedPositionHistoryEntry] = HistoryPage.of([], 3)

    assert page.entries == ()
    assert page.next is None
