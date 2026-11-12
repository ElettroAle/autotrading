from datetime import timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from autotrading.application.flows.errors import FlowExchangeUnavailableError, FlowLedgerIncompleteError
from autotrading.application.flows.record_account_executions import (
    OVERLAP,
    RecordAccountExecutionsCommand,
    RecordAccountExecutionsUseCase,
)
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.flows.ledger import ExecutionKind
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.account_activity import FakeAccountActivityAdapter
from tests.fakes.flow_ledger import InMemoryFlowLedgerAdapter
from tests.fakes.flow_repository import FlowStore, InMemoryFlowRepositoryAdapter
from tests.fakes.platform_orders import InMemoryPlatformOrdersAdapter
from tests.support.activity import READ_AT, a_fill, a_payment
from tests.support.flows import a_configuration, a_flow

TENANT = TenantId(uuid4())
ACCOUNT = uuid4()
EARLIER = READ_AT - timedelta(minutes=10)


class Bench:
    def __init__(self) -> None:
        self.store = FlowStore()
        self.exchange = FakeAccountActivityAdapter()
        self.orders = InMemoryPlatformOrdersAdapter()
        self.ledger = InMemoryFlowLedgerAdapter()
        self.use_case = RecordAccountExecutionsUseCase(
            InMemoryFlowRepositoryAdapter(self.store, TENANT), self.exchange, self.orders, self.ledger
        )

    def flow(self, *assets: str, account_id: UUID = ACCOUNT) -> Flow:
        flow = a_flow(
            TENANT, account_id=account_id, status=FlowStatus.ACTIVE, configuration=a_configuration(assets=assets)
        )
        self.store.flows.append(flow)
        return flow

    def order_of(self, flow: Flow | None) -> UUID:
        order = uuid4()
        self.orders.add(order, ACCOUNT, None if flow is None else flow.id)
        return order

    def record(self) -> list[tuple[str, ExecutionKind]]:
        entries = self.use_case.execute(RecordAccountExecutionsCommand(ACCOUNT))
        return [(entry.execution.fill_id, entry.kind) for entry in entries]


@pytest.fixture
def bench() -> Bench:
    return Bench()


def test_the_first_time_everything_the_exchange_keeps_enters_the_ledger(bench: Bench) -> None:
    flow = bench.flow("BTC")
    order = bench.order_of(flow)
    bench.exchange.executions[ACCOUNT] = [
        a_fill("BTC", order, fill_id="1", realized_pnl=Decimal(5), fee=Decimal(1), executed_at=EARLIER),
        a_fill("SOL", None, fill_id="2"),
    ]

    recorded = bench.record()

    assert recorded == [("1", ExecutionKind.FLOW_ORDER), ("2", ExecutionKind.UNATTRIBUTED)]
    assert bench.ledger.cursors[ACCOUNT] == READ_AT
    assert (bench.ledger.totals[flow.id].realized_pnl, bench.ledger.totals[flow.id].fees) == (Decimal(5), Decimal(1))


def test_only_what_is_newer_than_the_cursor_less_the_overlap_is_read(bench: Bench) -> None:
    bench.flow("BTC")
    bench.ledger.cursors[ACCOUNT] = READ_AT
    bench.exchange.executions[ACCOUNT] = [
        a_fill("BTC", None, fill_id="old", executed_at=READ_AT - OVERLAP - timedelta(seconds=1)),
        a_fill("BTC", None, fill_id="late", executed_at=READ_AT - OVERLAP),
    ]

    assert bench.record() == [("late", ExecutionKind.UNATTRIBUTED)]


def test_what_the_overlap_reads_again_is_not_recorded_twice(bench: Bench) -> None:
    flow = bench.flow("BTC")
    order = bench.order_of(flow)
    bench.exchange.executions[ACCOUNT] = [a_fill("BTC", order, realized_pnl=Decimal(5))]
    bench.exchange.funding[ACCOUNT] = [a_payment("BTC", Decimal(-1))]
    bench.record()

    assert bench.record() == []
    assert bench.ledger.realized(flow.id) == Decimal(5)
    assert len(bench.ledger.funding[ACCOUNT]) == 1


def test_without_anything_new_the_ledger_is_not_written(bench: Bench) -> None:
    bench.flow("BTC")

    assert bench.record() == []
    assert ACCOUNT not in bench.ledger.cursors


def test_an_incomplete_window_stops_the_recording_and_names_the_account(bench: Bench) -> None:
    bench.ledger.cursors[ACCOUNT] = EARLIER
    bench.exchange.complete = False
    bench.exchange.executions[ACCOUNT] = [a_fill("BTC", None)]

    with pytest.raises(FlowLedgerIncompleteError) as raised:
        bench.record()

    assert raised.value.account_id == ACCOUNT
    assert raised.value.permanent
    assert str(raised.value) == "registro delle esecuzioni incompleto"
    assert bench.ledger.entries == {}


def test_an_exchange_out_of_reach_records_nothing(bench: Bench) -> None:
    bench.exchange.reachable = False

    with pytest.raises(FlowExchangeUnavailableError):
        bench.record()

    assert bench.ledger.entries == {}


def test_a_closing_outside_of_the_position_opened_by_the_flow_is_its_own(bench: Bench) -> None:
    flow = bench.flow("BTC")
    order = bench.order_of(flow)
    bench.exchange.executions[ACCOUNT] = [a_fill("BTC", order, fill_id="1", size=Decimal(2), executed_at=EARLIER)]
    bench.record()
    bench.exchange.executions[ACCOUNT].append(
        a_fill("BTC", None, fill_id="2", size=Decimal(-2), start_position=Decimal(2), realized_pnl=Decimal(-3))
    )

    assert bench.record() == [("2", ExecutionKind.OUTSIDE_CLOSING)]
    assert bench.ledger.totals[flow.id].expected("BTC") == Decimal(0)
    assert bench.ledger.realized(flow.id) == Decimal(-3)


def test_a_manual_order_belongs_to_the_flow_of_the_asset(bench: Bench) -> None:
    flow = bench.flow("BTC")
    bench.exchange.executions[ACCOUNT] = [a_fill("BTC", bench.order_of(None), realized_pnl=Decimal(7))]

    bench.record()

    assert bench.ledger.realized(flow.id) == Decimal(7)


def test_only_the_orders_the_new_executions_name_are_asked(bench: Bench) -> None:
    flow = bench.flow("BTC")
    named, other = bench.order_of(flow), bench.order_of(flow)
    bench.exchange.executions[ACCOUNT] = [a_fill("BTC", named)]

    bench.record()

    assert bench.orders.asked == [frozenset({named})]
    assert other not in bench.orders.asked[0]


def test_the_flows_of_other_accounts_do_not_own_the_asset(bench: Bench) -> None:
    bench.flow("BTC", account_id=uuid4())
    bench.exchange.executions[ACCOUNT] = [a_fill("BTC", None, liquidation=True)]

    assert bench.record() == [("1", ExecutionKind.UNATTRIBUTED)]


def test_the_funding_of_the_position_of_the_flow_adds_to_its_totals(bench: Bench) -> None:
    flow = bench.flow("BTC")
    order = bench.order_of(flow)
    bench.exchange.executions[ACCOUNT] = [a_fill("BTC", order, size=Decimal(1), executed_at=EARLIER)]
    bench.exchange.funding[ACCOUNT] = [a_payment("BTC", Decimal("-0.25"))]

    bench.record()

    assert bench.ledger.totals[flow.id].funding == Decimal("-0.25")
    assert bench.ledger.recomputed(flow.id) == bench.ledger.totals[flow.id]


def test_what_the_overlap_reads_again_does_not_move_the_position_the_flow_expects(bench: Bench) -> None:
    flow = bench.flow("BTC")
    order = bench.order_of(flow)
    bench.exchange.executions[ACCOUNT] = [
        a_fill("BTC", order, fill_id="1", size=Decimal(2), executed_at=EARLIER - timedelta(minutes=5)),
        a_fill(
            "BTC", None, fill_id="2", size=Decimal(-1), start_position=Decimal(2), liquidation=True, executed_at=EARLIER
        ),
    ]
    bench.record()
    bench.exchange.executions[ACCOUNT].append(
        a_fill("BTC", None, fill_id="3", size=Decimal(-1), start_position=Decimal(1))
    )

    assert bench.record() == [("3", ExecutionKind.OUTSIDE_CLOSING)]
