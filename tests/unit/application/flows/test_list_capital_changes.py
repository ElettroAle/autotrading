from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

from autotrading.application.flows.errors import FlowNotFoundError
from autotrading.application.flows.list_capital_changes import ListCapitalChangesCommand, ListCapitalChangesUseCase
from autotrading.domain.flows.capital_change import CapitalChange, CapitalChangeReason
from autotrading.domain.flows.capital_history import CAPITAL_CHANGES_PER_PAGE, CapitalHistoryEntry
from autotrading.domain.flows.errors import InvalidPageNumberError
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.statistics_period import TimeWindow
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId
from tests.fakes.flow_repository import FlowStore, InMemoryFlowRepositoryAdapter
from tests.support.flows import a_flow

TENANT = TenantId.new()
AT = datetime(2026, 11, 10, 9, tzinfo=UTC)


class Bench:
    def __init__(self) -> None:
        self.store = FlowStore()
        self.repository = InMemoryFlowRepositoryAdapter(self.store, TENANT)
        self.list_changes = ListCapitalChangesUseCase(self.repository, "USDC")

    def saved(self, name: str = "alfa", tenant_id: TenantId = TENANT) -> Flow:
        flow = a_flow(tenant_id, name=name)
        self.store.flows.append(flow)
        self.store.save_version(flow)
        return flow

    def changed(self, flow: Flow, at: datetime, new: int = 700) -> CapitalChange:
        change = CapitalChange(
            flow.id, at, Decimal(500), Decimal(new), UserId("anna"), CapitalChangeReason.INCREASE, Decimal(new - 500)
        )
        self.store.capital_changes.setdefault(flow.id, []).append(change)
        return change


@pytest.fixture
def bench() -> Bench:
    return Bench()


def test_the_changes_of_the_flow_come_newest_first_with_its_name(bench: Bench) -> None:
    flow, other = bench.saved(), bench.saved("beta")
    older, newer = bench.changed(flow, AT), bench.changed(flow, AT + timedelta(days=1), 800)
    bench.changed(other, AT)

    page = bench.list_changes.execute(ListCapitalChangesCommand(flow.id))

    assert page.entries == (CapitalHistoryEntry.of_change(newer, "alfa"), CapitalHistoryEntry.of_change(older, "alfa"))
    assert (page.number, page.has_next, page.total, page.currency) == (1, False, 2, "USDC")


def test_only_the_changes_of_the_period_are_listed_and_counted(bench: Bench) -> None:
    flow = bench.saved()
    bench.changed(flow, datetime(2026, 11, 10, 10, tzinfo=UTC))
    kept = bench.changed(flow, datetime(2026, 11, 15, 10, tzinfo=UTC))
    window = TimeWindow.of_days(date(2026, 11, 14), date(2026, 11, 16))

    page = bench.list_changes.execute(ListCapitalChangesCommand(flow.id, window=window))

    assert page.entries == (CapitalHistoryEntry.of_change(kept, "alfa"),)
    assert page.total == 1


def test_the_changes_come_in_pages_and_a_page_says_whether_another_follows(bench: Bench) -> None:
    flow = bench.saved()
    changes = [bench.changed(flow, AT + timedelta(minutes=minute)) for minute in range(CAPITAL_CHANGES_PER_PAGE + 1)]

    first = bench.list_changes.execute(ListCapitalChangesCommand(flow.id))
    second = bench.list_changes.execute(ListCapitalChangesCommand(flow.id, page=2))

    assert (len(first.entries), first.has_next, first.total) == (CAPITAL_CHANGES_PER_PAGE, True, 51)
    assert second.entries == (CapitalHistoryEntry.of_change(changes[0], "alfa"),)
    assert (second.number, second.has_next) == (2, False)


def test_a_page_before_the_first_is_refused(bench: Bench) -> None:
    flow = bench.saved()

    with pytest.raises(InvalidPageNumberError):
        bench.list_changes.execute(ListCapitalChangesCommand(flow.id, page=0))


def test_the_history_of_a_flow_of_another_tenant_is_not_found(bench: Bench) -> None:
    theirs = bench.saved(tenant_id=TenantId.new())
    bench.changed(theirs, AT)

    with pytest.raises(FlowNotFoundError):
        bench.list_changes.execute(ListCapitalChangesCommand(theirs.id))
