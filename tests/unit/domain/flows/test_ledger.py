from datetime import timedelta
from decimal import Decimal
from types import MappingProxyType
from uuid import uuid4

from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.flows.ledger import (
    AccountLedger,
    Execution,
    ExecutionKind,
    ExecutionsWindow,
    FlowTotals,
    FundingEntry,
    FundingPayment,
    LedgerKeys,
    PlatformOrders,
)
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.support.activity import READ_AT, a_fill, a_payment
from tests.support.flows import a_configuration, a_flow

TENANT = TenantId(uuid4())
ACCOUNT = uuid4()
EARLIER = READ_AT - timedelta(minutes=10)


def flow_on(*assets: str, status: FlowStatus = FlowStatus.ACTIVE) -> Flow:
    return a_flow(TENANT, account_id=ACCOUNT, status=status, configuration=a_configuration(assets=assets))


def holding(flow: Flow, asset: str, size: Decimal) -> dict[FlowId, FlowTotals]:
    return {flow.id: FlowTotals(flow.id, positions=MappingProxyType({asset: size}))}


def attributed(
    flows: list[Flow],
    window: ExecutionsWindow,
    orders: PlatformOrders | None = None,
    totals: dict[FlowId, FlowTotals] | None = None,
) -> AccountLedger:
    return AccountLedger.attributed(flows, window, orders or {}, totals or {})


def window_of(*executions: Execution, funding: tuple[FundingPayment, ...] = ()) -> ExecutionsWindow:
    return ExecutionsWindow(executions, funding, complete=True)


def test_an_execution_of_an_order_of_the_flow_belongs_to_the_flow() -> None:
    flow, order = flow_on("BTC"), uuid4()

    (entry,) = attributed([flow], window_of(a_fill("BTC", order)), {order: flow.id}).entries

    assert (entry.flow_id, entry.kind, entry.platform_order) == (flow.id, ExecutionKind.FLOW_ORDER, True)


def test_an_order_of_the_platform_sent_for_no_flow_belongs_to_the_flow_that_owns_the_asset() -> None:
    flow, manual = flow_on("BTC"), uuid4()

    (entry,) = attributed([flow], window_of(a_fill("BTC", manual)), {manual: None}).entries

    assert (entry.flow_id, entry.kind, entry.platform_order) == (flow.id, ExecutionKind.FLOW_ORDER, True)


def test_an_order_of_the_platform_for_no_flow_on_an_asset_of_no_flow_belongs_to_no_flow() -> None:
    manual = uuid4()

    (entry,) = attributed([flow_on("BTC")], window_of(a_fill("SOL", manual)), {manual: None}).entries

    assert (entry.flow_id, entry.kind, entry.platform_order) == (None, ExecutionKind.UNATTRIBUTED, True)


def test_a_liquidation_without_an_order_of_the_platform_belongs_to_the_flow_of_the_asset() -> None:
    flow = flow_on("BTC")

    (entry,) = attributed([flow], window_of(a_fill("BTC", None, liquidation=True))).entries

    assert (entry.flow_id, entry.kind, entry.platform_order) == (flow.id, ExecutionKind.LIQUIDATION, False)


def test_a_closing_of_exactly_the_position_of_the_flow_belongs_to_the_flow() -> None:
    flow = flow_on("BTC")
    closing = a_fill("BTC", None, size=Decimal(-2), start_position=Decimal(2))

    (entry,) = attributed([flow], window_of(closing), totals=holding(flow, "BTC", Decimal(2))).entries

    assert (entry.flow_id, entry.kind) == (flow.id, ExecutionKind.OUTSIDE_CLOSING)


def test_a_partial_closing_outside_belongs_to_no_flow() -> None:
    flow = flow_on("BTC")
    partial = a_fill("BTC", None, size=Decimal(-1), start_position=Decimal(2))

    (entry,) = attributed([flow], window_of(partial), totals=holding(flow, "BTC", Decimal(2))).entries

    assert (entry.flow_id, entry.kind) == (None, ExecutionKind.UNATTRIBUTED)


def test_a_closing_of_a_position_bigger_than_the_one_of_the_flow_belongs_to_no_flow() -> None:
    flow = flow_on("BTC")
    bigger = a_fill("BTC", None, size=Decimal(-3), start_position=Decimal(3))

    (entry,) = attributed([flow], window_of(bigger), totals=holding(flow, "BTC", Decimal(2))).entries

    assert entry.flow_id is None


def test_an_execution_outside_with_no_position_of_the_flow_belongs_to_no_flow() -> None:
    flow = flow_on("BTC")

    (entry,) = attributed([flow], window_of(a_fill("BTC", None, size=Decimal(0)))).entries

    assert (entry.flow_id, entry.kind) == (None, ExecutionKind.UNATTRIBUTED)


def test_an_execution_on_an_asset_of_no_flow_belongs_to_no_flow() -> None:
    (entry,) = attributed([flow_on("BTC")], window_of(a_fill("SOL", None, liquidation=True))).entries

    assert (entry.flow_id, entry.kind) == (None, ExecutionKind.UNATTRIBUTED)


def test_an_archived_flow_owns_no_asset() -> None:
    flow, manual = flow_on("BTC", status=FlowStatus.ARCHIVED), uuid4()

    (entry,) = attributed([flow], window_of(a_fill("BTC", manual)), {manual: None}).entries

    assert entry.flow_id is None


def test_the_position_opened_by_the_flow_in_the_same_window_is_the_one_its_closing_matches() -> None:
    flow, order = flow_on("BTC"), uuid4()
    opening = a_fill("BTC", order, fill_id="1", size=Decimal(2), executed_at=EARLIER)
    closing = a_fill("BTC", None, fill_id="2", size=Decimal(-2), start_position=Decimal(2))

    ledger = attributed([flow], window_of(closing, opening), {order: flow.id})

    assert [(entry.execution.fill_id, entry.kind) for entry in ledger.entries] == [
        ("1", ExecutionKind.FLOW_ORDER),
        ("2", ExecutionKind.OUTSIDE_CLOSING),
    ]


def test_funding_belongs_to_the_flow_holding_a_position_on_the_asset() -> None:
    flow = flow_on("BTC")
    payment = a_payment("BTC", Decimal("-0.3"))

    ledger = attributed([flow], window_of(funding=(payment,)), totals=holding(flow, "BTC", Decimal(1)))

    assert ledger.funding == (FundingEntry(payment, flow.id),)


def test_funding_of_a_position_no_flow_holds_belongs_to_no_flow() -> None:
    payments = (a_payment("BTC", Decimal(1)), a_payment("SOL", Decimal(1)))

    ledger = attributed([flow_on("BTC")], window_of(funding=payments))

    assert [entry.flow_id for entry in ledger.funding] == [None, None]


def test_funding_paid_after_the_flow_closed_belongs_to_no_flow() -> None:
    flow, order = flow_on("BTC"), uuid4()
    closing = a_fill("BTC", order, size=Decimal(-1), executed_at=EARLIER)

    ledger = attributed(
        [flow],
        window_of(closing, funding=(a_payment("BTC", Decimal(1)),)),
        {order: flow.id},
        holding(flow, "BTC", Decimal(1)),
    )

    assert [entry.flow_id for entry in ledger.funding] == [None]


def test_the_latest_moment_is_that_of_the_newest_execution_or_payment() -> None:
    flow = flow_on("BTC")
    window = window_of(a_fill("BTC", None, executed_at=EARLIER), funding=(a_payment("BTC", Decimal(1)),))

    assert attributed([flow], window).latest == READ_AT
    assert attributed([flow], window_of()).latest is None


def test_the_totals_add_realized_pnl_fees_funding_and_the_signed_size() -> None:
    flow = flow_on("BTC")
    totals = (
        FlowTotals(flow.id)
        .with_execution(a_fill("BTC", None, size=Decimal(2), realized_pnl=Decimal(5), fee=Decimal(1)))
        .with_execution(a_fill("BTC", None, size=Decimal(-1), realized_pnl=Decimal(-2), fee=Decimal(1)))
        .with_funding(a_payment("BTC", Decimal("-0.5")))
    )

    assert (totals.realized_pnl, totals.fees, totals.funding) == (Decimal(3), Decimal(2), Decimal("-0.5"))
    assert (totals.expected("BTC"), totals.expected("ETH")) == (Decimal(1), Decimal(0))


def test_the_keys_already_recorded_leave_only_the_unknown_part_of_the_window() -> None:
    known, new = a_fill("BTC", None, fill_id="1"), a_fill("BTC", None, fill_id="2")
    paid, unpaid = a_payment("BTC", Decimal(1), paid_at=EARLIER), a_payment("BTC", Decimal(1))
    keys = LedgerKeys(frozenset({known.key}), frozenset({paid.key}))

    unknown = keys.unknown_in(window_of(known, new, funding=(paid, unpaid)))

    assert (unknown.executions, unknown.funding) == ((new,), (unpaid,))
