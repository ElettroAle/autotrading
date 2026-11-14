from datetime import UTC, date, datetime, timedelta

from autotrading.application.flows.query_closed_position_history import (
    QueryClosedPositionHistoryCommand,
    QueryClosedPositionHistoryUseCase,
)
from autotrading.domain.flows.history import HistoryFilter
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
    period = StatisticsPeriod.named("range", date(2026, 11, 10), date(2026, 11, 20))

    page = use_case.execute(QueryClosedPositionHistoryCommand(HistoryFilter(period=period, asset="ETH"), None))

    closed = [entry.position.closing.at for entry in page.entries]
    assert {entry.position.asset for entry in page.entries} == {"ETH"}
    assert closed == sorted(closed, reverse=True)
    assert (min(closed).day, max(closed).day, len(closed)) == (10, 20, 11)


def test_gives_pages_of_50_and_where_the_next_starts() -> None:
    rows = [a_position_row(FIRST + timedelta(hours=hour)) for hour in range(51)]
    use_case = QueryClosedPositionHistoryUseCase(
        InMemoryFlowHistoryAdapter(HistoryStore(closed_positions=rows)), lambda: NOW
    )

    first = use_case.execute(QueryClosedPositionHistoryCommand(HistoryFilter(), None))
    last = use_case.execute(QueryClosedPositionHistoryCommand(HistoryFilter(), first.next))

    assert (len(first.entries), first.next) == (50, first.entries[-1].cursor)
    assert (len(last.entries), last.next) == (1, None)
