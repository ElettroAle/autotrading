from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from autotrading.application.flows.errors import FlowAccountNotFoundError, FlowExchangeUnavailableError
from autotrading.application.flows.list_account_capital_changes import (
    ListAccountCapitalChangesCommand,
    ListAccountCapitalChangesUseCase,
)
from autotrading.domain.flows.capital_change import CapitalChange, CapitalChangeReason
from autotrading.domain.flows.capital_history import (
    CAPITAL_CHANGES_PER_PAGE,
    AccountTransfer,
    CapitalHistoryEntry,
    TransferDirection,
)
from autotrading.domain.flows.errors import InvalidPageNumberError
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.statistics_period import TimeWindow
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId
from tests.fakes.account_transfers import FakeAccountTransfersAdapter
from tests.fakes.flow_repository import FlowStore, InMemoryFlowRepositoryAdapter
from tests.support.flows import a_flow

TENANT = TenantId.new()
AT = datetime(2026, 11, 10, 9, tzinfo=UTC)


class Bench:
    def __init__(self) -> None:
        self.store = FlowStore()
        self.transfers = FakeAccountTransfersAdapter()
        self.account_id = uuid4()
        self.list_changes = ListAccountCapitalChangesUseCase(
            InMemoryFlowRepositoryAdapter(self.store, TENANT), self.transfers, "USDC"
        )

    def saved(self, name: str, *, account_id: UUID | None = None, tenant_id: TenantId = TENANT) -> Flow:
        flow = a_flow(tenant_id, name=name, account_id=account_id or self.account_id)
        self.store.flows.append(flow)
        self.store.save_version(flow)
        return flow

    def changed(self, flow: Flow, at: datetime) -> CapitalChange:
        change = CapitalChange(
            flow.id, at, Decimal(500), Decimal(700), UserId("anna"), CapitalChangeReason.INCREASE, Decimal(200)
        )
        self.store.capital_changes.setdefault(flow.id, []).append(change)
        return change

    def declared(self, at: datetime, direction: TransferDirection = TransferDirection.DEPOSIT) -> AccountTransfer:
        transfer = AccountTransfer(at, Decimal(300), direction)
        self.transfers.declared.setdefault(self.account_id, []).append(transfer)
        return transfer


@pytest.fixture
def bench() -> Bench:
    return Bench()


def test_the_changes_of_every_flow_of_the_account_and_its_transfers_come_newest_first(bench: Bench) -> None:
    alfa, beta = bench.saved("alfa"), bench.saved("beta")
    first = bench.changed(alfa, AT)
    deposit = bench.declared(AT + timedelta(hours=1))
    second = bench.changed(beta, AT + timedelta(hours=2))
    withdrawal = bench.declared(AT + timedelta(hours=3), TransferDirection.WITHDRAWAL)

    page = bench.list_changes.execute(ListAccountCapitalChangesCommand(bench.account_id))

    assert page.entries == (
        CapitalHistoryEntry.of_transfer(withdrawal),
        CapitalHistoryEntry.of_change(second, "beta"),
        CapitalHistoryEntry.of_transfer(deposit),
        CapitalHistoryEntry.of_change(first, "alfa"),
    )
    assert (page.number, page.has_next, page.total, page.currency) == (1, False, 4, "USDC")


def test_the_flows_of_other_accounts_are_left_out(bench: Bench) -> None:
    elsewhere = bench.saved("gamma", account_id=uuid4())
    bench.changed(elsewhere, AT)

    page = bench.list_changes.execute(ListAccountCapitalChangesCommand(bench.account_id))

    assert (page.entries, page.total) == ((), 0)


def test_the_period_narrows_both_the_changes_and_the_transfers(bench: Bench) -> None:
    alfa = bench.saved("alfa")
    bench.changed(alfa, datetime(2026, 11, 10, 10, tzinfo=UTC))
    bench.declared(datetime(2026, 11, 13, 23, 59, tzinfo=UTC))
    kept_change = bench.changed(alfa, datetime(2026, 11, 15, 10, tzinfo=UTC))
    kept_transfer = bench.declared(datetime(2026, 11, 16, 23, 59, tzinfo=UTC))
    window = TimeWindow.of_days(date(2026, 11, 14), date(2026, 11, 16))

    page = bench.list_changes.execute(ListAccountCapitalChangesCommand(bench.account_id, window=window))

    assert page.entries == (
        CapitalHistoryEntry.of_transfer(kept_transfer),
        CapitalHistoryEntry.of_change(kept_change, "alfa"),
    )
    assert page.total == 2
    assert bench.transfers.windows == [window]


def test_the_rows_of_both_sources_come_in_pages(bench: Bench) -> None:
    alfa = bench.saved("alfa")
    for minute in range(CAPITAL_CHANGES_PER_PAGE):
        bench.changed(alfa, AT + timedelta(minutes=2 * minute + 1))
        bench.declared(AT + timedelta(minutes=2 * minute))

    first = bench.list_changes.execute(ListAccountCapitalChangesCommand(bench.account_id))
    second = bench.list_changes.execute(ListAccountCapitalChangesCommand(bench.account_id, page=2))

    assert (len(first.entries), first.has_next, first.total) == (CAPITAL_CHANGES_PER_PAGE, True, 100)
    assert (len(second.entries), second.has_next) == (CAPITAL_CHANGES_PER_PAGE, False)
    assert first.entries[-1].occurred_at > second.entries[0].occurred_at
    assert second.entries[-1].occurred_at == AT


def test_a_page_before_the_first_is_refused_before_reading_the_exchange(bench: Bench) -> None:
    with pytest.raises(InvalidPageNumberError):
        bench.list_changes.execute(ListAccountCapitalChangesCommand(bench.account_id, page=0))

    assert bench.transfers.windows == []


def test_an_exchange_out_of_reach_gives_no_history_rather_than_a_part_of_it(bench: Bench) -> None:
    bench.changed(bench.saved("alfa"), AT)
    bench.transfers.reachable = False

    with pytest.raises(FlowExchangeUnavailableError):
        bench.list_changes.execute(ListAccountCapitalChangesCommand(bench.account_id))


def test_an_account_the_tenant_does_not_have_is_not_found(bench: Bench) -> None:
    bench.transfers.missing.add(bench.account_id)

    with pytest.raises(FlowAccountNotFoundError):
        bench.list_changes.execute(ListAccountCapitalChangesCommand(bench.account_id))


def test_the_changes_of_another_tenant_on_an_account_of_the_same_id_are_left_out(bench: Bench) -> None:
    theirs = bench.saved("gamma", tenant_id=TenantId.new())
    bench.changed(theirs, AT)

    page = bench.list_changes.execute(ListAccountCapitalChangesCommand(bench.account_id))

    assert (page.entries, page.total) == ((), 0)
