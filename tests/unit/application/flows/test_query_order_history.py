from datetime import UTC, datetime, timedelta
from uuid import uuid4

from autotrading.application.flows.query_order_history import QueryOrderHistoryCommand, QueryOrderHistoryUseCase
from autotrading.domain.flows.history import HistoryFilter
from tests.fakes.flow_history import HistoryStore, InMemoryFlowHistoryAdapter
from tests.support.history import ACCOUNT, an_order_row

NOW = datetime(2026, 11, 30, 23, 0, tzinfo=UTC)
FIRST = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)


def test_gives_the_orders_of_an_account_with_their_executions() -> None:
    rows = [an_order_row(FIRST + timedelta(days=day)) for day in range(3)]
    rows.append(an_order_row(FIRST, account_id=uuid4()))
    use_case = QueryOrderHistoryUseCase(InMemoryFlowHistoryAdapter(HistoryStore(orders=rows)), lambda: NOW)

    page = use_case.execute(QueryOrderHistoryCommand(HistoryFilter(account_id=ACCOUNT), None))

    assert [entry.created_at for entry in page.entries] == [FIRST + timedelta(days=day) for day in (2, 1, 0)]
    assert {entry.account_id for entry in page.entries} == {ACCOUNT}
    assert all(len(entry.executions) == 2 for entry in page.entries)
    assert page.next is None


def test_gives_pages_of_50_and_where_the_next_starts() -> None:
    rows = [an_order_row(FIRST + timedelta(minutes=minute)) for minute in range(60)]
    use_case = QueryOrderHistoryUseCase(InMemoryFlowHistoryAdapter(HistoryStore(orders=rows)), lambda: NOW)

    first = use_case.execute(QueryOrderHistoryCommand(HistoryFilter(), None))
    last = use_case.execute(QueryOrderHistoryCommand(HistoryFilter(), first.next))

    assert (len(first.entries), first.next) == (50, first.entries[-1].cursor)
    assert (len(last.entries), last.next) == (10, None)
