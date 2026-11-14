from datetime import UTC, date, datetime, timedelta

from autotrading.application.flows.query_cycle_history import QueryCycleHistoryCommand, QueryCycleHistoryUseCase
from autotrading.domain.flows.history import HistoryCursor, HistoryFilter
from autotrading.domain.flows.statistics_period import StatisticsPeriod, TimeWindow
from tests.fakes.flow_history import HistoryStore, InMemoryFlowHistoryAdapter
from tests.support.history import FLOW, a_cycle_row

NOW = datetime(2026, 11, 30, 23, 0, tzinfo=UTC)
FIRST = datetime(2026, 11, 1, 0, 0, tzinfo=UTC)


def use_case_on(store: HistoryStore) -> tuple[QueryCycleHistoryUseCase, InMemoryFlowHistoryAdapter]:
    history = InMemoryFlowHistoryAdapter(store)
    return QueryCycleHistoryUseCase(history, lambda: NOW), history


def test_gives_the_cycles_of_a_version_from_the_most_recent() -> None:
    store = HistoryStore([a_cycle_row(FIRST + timedelta(days=day), version=1 if day < 14 else 2) for day in range(30)])
    use_case, _ = use_case_on(store)

    page = use_case.execute(QueryCycleHistoryCommand(HistoryFilter(flow_id=FLOW, version=2), None))

    planned = [entry.record.planned_at for entry in page.entries]
    assert planned == sorted(planned, reverse=True)
    assert min(planned) == datetime(2026, 11, 15, tzinfo=UTC)
    assert len(planned) == 16
    assert page.next is None


def test_gives_pages_of_50_and_where_the_next_starts() -> None:
    store = HistoryStore([a_cycle_row(FIRST + timedelta(hours=hour)) for hour in range(120)])
    use_case, _ = use_case_on(store)

    first = use_case.execute(QueryCycleHistoryCommand(HistoryFilter(), None))
    second = use_case.execute(QueryCycleHistoryCommand(HistoryFilter(), first.next))

    assert len(first.entries) == len(second.entries) == 50
    assert first.next == first.entries[-1].cursor
    assert second.entries[0].record.planned_at == first.entries[-1].record.planned_at - timedelta(hours=1)


def test_reads_the_period_at_the_instant_of_the_clock() -> None:
    use_case, history = use_case_on(HistoryStore())
    after = HistoryCursor(NOW, FLOW)

    use_case.execute(QueryCycleHistoryCommand(HistoryFilter(period=StatisticsPeriod.named("7d")), after))

    assert history.queries[-1].window == TimeWindow(since=NOW - timedelta(days=7))
    assert history.queries[-1].after == after


def test_gives_nothing_when_no_cycle_matches() -> None:
    period = StatisticsPeriod.named("range", date(2026, 12, 1), date(2026, 12, 2))
    use_case, _ = use_case_on(HistoryStore([a_cycle_row(FIRST)]))

    page = use_case.execute(QueryCycleHistoryCommand(HistoryFilter(period=period), None))

    assert page.entries == ()
    assert page.next is None
