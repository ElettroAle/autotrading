from datetime import UTC, datetime, timedelta
from decimal import Decimal

from autotrading.application.flows.query_closed_position_history import (
    QueryClosedPositionHistoryCommand,
    QueryClosedPositionHistoryUseCase,
)
from autotrading.domain.flows.history import ClosedPositionHistoryTotals, HistoryFilter
from autotrading.domain.flows.statistics_period import StatisticsPeriod
from tests.fakes.flow_history import HistoryStore, InMemoryFlowHistoryAdapter
from tests.support.history import a_position_row

NOW = datetime(2026, 11, 30, 23, 0, tzinfo=UTC)
FIRST = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)


def test_gives_the_positions_of_an_asset_closed_in_the_period() -> None:
    rows = [a_position_row(FIRST + timedelta(days=day), asset=asset) for day in range(30) for asset in ("BTC", "ETH")]
    use_case = QueryClosedPositionHistoryUseCase(
        InMemoryFlowHistoryAdapter(HistoryStore(closed_positions=rows)), lambda: NOW
    )
    period = StatisticsPeriod.named(
        "range", datetime(2026, 11, 10, tzinfo=UTC), datetime(2026, 11, 20, 23, 59, tzinfo=UTC)
    )

    page = use_case.execute(QueryClosedPositionHistoryCommand(HistoryFilter(period=period, asset="ETH"), None)).page

    closed = [entry.position.closing.at for entry in page.entries]
    assert {entry.position.asset for entry in page.entries} == {"ETH"}
    assert closed == sorted(closed, reverse=True)
    assert (min(closed).day, max(closed).day, len(closed)) == (10, 20, 11)


def test_gives_pages_of_50_and_where_the_next_starts() -> None:
    rows = [a_position_row(FIRST + timedelta(hours=hour)) for hour in range(51)]
    use_case = QueryClosedPositionHistoryUseCase(
        InMemoryFlowHistoryAdapter(HistoryStore(closed_positions=rows)), lambda: NOW
    )

    first = use_case.execute(QueryClosedPositionHistoryCommand(HistoryFilter(), None)).page
    last = use_case.execute(QueryClosedPositionHistoryCommand(HistoryFilter(), first.next)).page

    assert (len(first.entries), first.next) == (50, first.entries[-1].cursor)
    assert (len(last.entries), last.next) == (1, None)


def test_the_first_page_comes_with_the_totals_of_every_position_of_the_filter() -> None:
    rows = [
        a_position_row(FIRST + timedelta(hours=hour), asset=asset) for hour in range(60) for asset in ("BTC", "ETH")
    ]
    use_case = QueryClosedPositionHistoryUseCase(
        InMemoryFlowHistoryAdapter(HistoryStore(closed_positions=rows)), lambda: NOW
    )

    report = use_case.execute(QueryClosedPositionHistoryCommand(HistoryFilter(asset="ETH"), None))

    assert len(report.page.entries) == 50
    assert report.totals == ClosedPositionHistoryTotals(pnl=Decimal(600), fees=Decimal("25.2"))


def test_the_following_pages_come_without_totals() -> None:
    rows = [a_position_row(FIRST + timedelta(hours=hour)) for hour in range(51)]
    history = InMemoryFlowHistoryAdapter(HistoryStore(closed_positions=rows))
    use_case = QueryClosedPositionHistoryUseCase(history, lambda: NOW)
    first = use_case.execute(QueryClosedPositionHistoryCommand(HistoryFilter(), None))

    last = use_case.execute(QueryClosedPositionHistoryCommand(HistoryFilter(), first.page.next))

    assert (last.totals, len(last.page.entries)) == (None, 1)
    assert history.totals_queries == [history.queries[0]]
