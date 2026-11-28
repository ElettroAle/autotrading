from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from autotrading.domain.flows.account_activity import AccountActivity
from autotrading.domain.flows.account_reconciliation import (
    AccountReading,
    AccountReconciliation,
    OutsideClosing,
)
from autotrading.domain.flows.balance_comparison import BalanceComparison
from autotrading.domain.flows.closed_position import CloseReason
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.flows.ledger import (
    AccountLedger,
    BalanceMovement,
    Execution,
    ExecutionKind,
    FundingEntry,
    LedgerEntry,
)
from autotrading.domain.flows.reconciliation_alarm import ReconciliationAlarm
from autotrading.domain.flows.unattributable import UnattributableItem, UnattributableKind
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.support.activity import READ_AT, a_fill, a_movement, a_payment, a_position, an_activity
from tests.support.flows import a_configuration, a_flow

TENANT = TenantId(uuid4())
ACCOUNT = uuid4()
BEFORE = READ_AT - timedelta(minutes=5)


def flow_on(*assets: str, status: FlowStatus = FlowStatus.ACTIVE) -> Flow:
    return a_flow(TENANT, account_id=ACCOUNT, status=status, configuration=a_configuration(assets=assets))


def previous(
    open_assets: dict[FlowId, frozenset[str]] | None = None, reference: Decimal | None = None
) -> AccountReading:
    return AccountReading(ACCOUNT, BEFORE, open_assets or {}, reference)


def of_platform(execution: Execution, flow: Flow | None = None) -> LedgerEntry:
    return LedgerEntry(execution, None if flow is None else flow.id, ExecutionKind.FLOW_ORDER, platform_order=True)


def unattributed(execution: Execution) -> LedgerEntry:
    return LedgerEntry(execution, None, ExecutionKind.UNATTRIBUTED)


def reconcile(
    flows: list[Flow],
    activity: AccountActivity | None = None,
    *,
    recorded: tuple[LedgerEntry, ...] = (),
    funding: tuple[FundingEntry, ...] = (),
    booked: tuple[LedgerEntry, ...] = (),
    booked_funding: tuple[FundingEntry, ...] = (),
    booked_movements: tuple[BalanceMovement, ...] = (),
    last: AccountReading | None = None,
    threshold: Decimal = Decimal(1),
) -> AccountReconciliation:
    """`recorded` and `funding` are what the ledger has just written; `booked`, `booked_funding` and
    `booked_movements` what it holds after the previous reading, whoever recorded it."""
    return AccountReconciliation.of(
        ACCOUNT,
        flows,
        activity or an_activity(),
        last,
        AccountLedger(recorded, funding),
        AccountLedger(booked, booked_funding, booked_movements),
        threshold,
    )


def test_a_position_on_an_asset_of_no_flow_is_unattributable() -> None:
    activity = an_activity(positions=(a_position("BTC"), a_position("SOL", size=Decimal(3))))

    result = reconcile([flow_on("BTC")], activity)

    assert result.items == (
        UnattributableItem(ACCOUNT, UnattributableKind.POSITION, "SOL", "SOL", Decimal(3), READ_AT),
    )


def test_an_archived_flow_owns_no_asset_any_more() -> None:
    result = reconcile([flow_on("SOL", status=FlowStatus.ARCHIVED)], an_activity(positions=(a_position("SOL"),)))

    assert [item.reference for item in result.items] == ["SOL"]


def test_a_new_execution_without_an_order_of_the_platform_is_unattributable() -> None:
    fill = a_fill("BTC", None, fill_id="77", size=Decimal(-2), executed_at=BEFORE)

    result = reconcile([flow_on("BTC")], recorded=(unattributed(fill),), last=previous())

    assert result.items == (UnattributableItem(ACCOUNT, UnattributableKind.FILL, "77", "BTC", Decimal(2), READ_AT),)


def test_a_new_execution_given_to_a_flow_without_an_order_of_the_platform_is_still_reported() -> None:
    flow = flow_on("BTC")
    entry = LedgerEntry(a_fill("BTC", None), flow.id, ExecutionKind.LIQUIDATION)

    result = reconcile([flow], recorded=(entry,), last=previous())

    assert [item.kind for item in result.items] == [UnattributableKind.FILL]


def test_an_execution_of_an_order_of_the_platform_is_explained_even_without_a_flow() -> None:
    result = reconcile([flow_on("BTC")], recorded=(of_platform(a_fill("BTC", uuid4())),), last=previous())

    assert result.items == ()


def test_without_a_previous_reading_the_past_executions_and_movements_are_the_starting_point() -> None:
    result = reconcile(
        [flow_on("BTC")],
        recorded=(unattributed(a_fill("BTC", None)),),
        booked_movements=(a_movement(Decimal(200)),),
    )

    assert result.items == ()
    assert result.closed_outside == ()


def test_a_movement_the_exchange_declares_is_no_unattributable_change_of_the_balance() -> None:
    movements = (a_movement(Decimal(200), movement_id="0x1"),)

    result = reconcile(
        [flow_on("BTC")],
        an_activity(balance=Decimal(1200)),
        booked_movements=movements,
        last=previous(reference=Decimal(1000)),
    )

    assert result.items == ()
    assert result.alarm is None


def test_a_position_of_a_flow_gone_from_the_exchange_was_closed_outside_the_platform() -> None:
    flow = flow_on("BTC")
    recorded = (
        unattributed(
            a_fill(
                "BTC",
                None,
                fill_id="1",
                realized_pnl=Decimal(-30),
                fee=Decimal(1),
                executed_at=READ_AT - timedelta(minutes=2),
            )
        ),
        unattributed(
            a_fill(
                "BTC",
                None,
                fill_id="2",
                realized_pnl=Decimal(-20),
                fee=Decimal(1),
                executed_at=READ_AT - timedelta(minutes=1),
            )
        ),
        unattributed(a_fill("ETH", None, fill_id="3", realized_pnl=Decimal(-99), fee=Decimal(9))),
    )

    result = reconcile([flow], recorded=recorded, last=previous({flow.id: frozenset({"BTC"})}))

    assert result.closed_outside == (
        OutsideClosing(flow.id, "BTC", Decimal(-50), Decimal(2), READ_AT - timedelta(minutes=1)),
    )


def test_a_position_of_a_flow_liquidated_was_closed_outside_by_a_liquidation() -> None:
    flow = flow_on("BTC")
    liquidation = a_fill("BTC", None, realized_pnl=Decimal(-48), liquidation=True)
    recorded = (LedgerEntry(liquidation, flow.id, ExecutionKind.LIQUIDATION),)

    result = reconcile([flow], recorded=recorded, last=previous({flow.id: frozenset({"BTC"})}))

    [closing] = result.closed_outside
    assert (closing.liquidation, closing.reason_told) == (True, CloseReason.LIQUIDATION)


def test_a_position_closed_outside_without_a_liquidation_keeps_the_reason_of_a_closing_outside() -> None:
    flow = flow_on("BTC")
    recorded = (unattributed(a_fill("BTC", None, realized_pnl=Decimal(-7))),)

    result = reconcile([flow], recorded=recorded, last=previous({flow.id: frozenset({"BTC"})}))

    [closing] = result.closed_outside
    assert (closing.liquidation, closing.reason_told) == (False, CloseReason.OUTSIDE_PLATFORM)


def test_a_position_closed_outside_without_executions_closes_at_the_reading() -> None:
    flow = flow_on("BTC")

    result = reconcile([flow], last=previous({flow.id: frozenset({"BTC"})}))

    assert result.closed_outside == (OutsideClosing(flow.id, "BTC", Decimal(0), Decimal(0), READ_AT),)


def test_the_outcome_of_a_closing_outside_ignores_the_executions_of_platform_orders_on_other_assets() -> None:
    flow = flow_on("BTC", "SOL")
    recorded = (
        of_platform(a_fill("SOL", uuid4(), fill_id="1", realized_pnl=Decimal(5)), flow),
        unattributed(a_fill("BTC", None, fill_id="2", realized_pnl=Decimal(-7))),
    )

    result = reconcile([flow], recorded=recorded, last=previous({flow.id: frozenset({"BTC"})}))

    assert [(closing.asset, closing.realized_pnl) for closing in result.closed_outside] == [("BTC", Decimal(-7))]


def test_a_position_the_platform_closed_with_its_own_order_is_not_closed_outside() -> None:
    flow = flow_on("BTC")

    result = reconcile(
        [flow], recorded=(of_platform(a_fill("BTC", uuid4()), flow),), last=previous({flow.id: frozenset({"BTC"})})
    )

    assert result.closed_outside == ()


def test_a_position_closed_by_the_manual_command_alone_is_not_closed_outside() -> None:
    flow = flow_on("BTC")

    result = reconcile(
        [flow], recorded=(of_platform(a_fill("BTC", uuid4())),), last=previous({flow.id: frozenset({"BTC"})})
    )

    assert result.closed_outside == ()


def test_a_position_still_open_is_not_closed() -> None:
    flow = flow_on("BTC")

    result = reconcile(
        [flow], an_activity(positions=(a_position("BTC"),)), last=previous({flow.id: frozenset({"BTC"})})
    )

    assert result.closed_outside == ()


def test_a_flow_archived_since_the_last_reading_has_nothing_closed_outside() -> None:
    flow = flow_on("BTC", status=FlowStatus.ARCHIVED)

    result = reconcile([flow], last=previous({flow.id: frozenset({"BTC"})}))

    assert result.closed_outside == ()


def test_the_new_reading_keeps_the_open_assets_of_each_flow() -> None:
    alfa, beta = flow_on("BTC", "SOL"), flow_on("ETH")

    result = reconcile([alfa, beta], an_activity(positions=(a_position("BTC"), a_position("DOGE"))))

    assert result.reading.open_assets == {alfa.id: frozenset({"BTC"}), beta.id: frozenset()}
    assert result.reading.read_at == READ_AT


def test_the_assets_open_on_the_account_are_those_of_the_reading() -> None:
    result = reconcile([flow_on("BTC")], an_activity(positions=(a_position("BTC"), a_position("SOL"))))

    assert result.open_assets == frozenset({"BTC", "SOL"})


# The balance of the account (R3.3.1)


def test_the_first_reading_takes_the_balance_read_as_reference_without_comparing() -> None:
    activity = an_activity(balance=Decimal(1000), positions=(a_position("BTC", unrealized_pnl=Decimal(30)),))

    result = reconcile([flow_on("BTC")], activity)

    assert result.comparison is None
    assert result.alarm is None
    assert result.reading.reference_balance == Decimal(970)


def test_a_reading_saved_without_reference_takes_the_balance_read_as_reference() -> None:
    result = reconcile([flow_on("BTC")], an_activity(balance=Decimal(980)), last=previous())

    assert result.comparison is None
    assert result.reading.reference_balance == Decimal(980)


def test_the_read_balance_leaves_out_the_unrealized_pnl_of_the_open_positions() -> None:
    activity = an_activity(balance=Decimal(1040), positions=(a_position("BTC", unrealized_pnl=Decimal(40)),))

    result = reconcile([flow_on("BTC")], activity, last=previous(reference=Decimal(1000)))

    assert result.comparison == BalanceComparison(Decimal(1000), Decimal(1000), READ_AT)
    assert result.items == ()


def test_the_executions_fees_and_funding_of_the_flows_explain_the_balance() -> None:
    flow = flow_on("BTC")
    fill = a_fill("BTC", uuid4(), realized_pnl=Decimal(30), fee=Decimal(2))
    funding = (FundingEntry(a_payment("BTC", Decimal(-3)), flow.id),)

    result = reconcile(
        [flow],
        an_activity(balance=Decimal(1025)),
        booked=(of_platform(fill, flow),),
        booked_funding=funding,
        last=previous(reference=Decimal(1000)),
    )

    assert result.comparison == BalanceComparison(Decimal(1025), Decimal(1025), READ_AT)


# ADR saldo-atteso-con-le-sole-righe-successive-alla-lettura-precedente: a row published late was in the balance read
# by the previous reading, which became the reference (Bug 506).
@pytest.mark.parametrize(
    ("executed_at", "expected"),
    [(BEFORE - timedelta(minutes=1), Decimal(1000)), (BEFORE, Decimal(1000)), (READ_AT, Decimal(1028))],
)
def test_an_execution_of_a_flow_explains_the_balance_only_after_the_previous_reading(
    executed_at: datetime, expected: Decimal
) -> None:
    flow = flow_on("BTC")
    fill = a_fill("BTC", uuid4(), realized_pnl=Decimal(30), fee=Decimal(2), executed_at=executed_at)

    result = reconcile(
        [flow],
        an_activity(balance=expected),
        booked=(of_platform(fill, flow),),
        last=previous(reference=Decimal(1000)),
    )

    assert result.comparison == BalanceComparison(expected, expected, READ_AT)
    assert result.items == ()


@pytest.mark.parametrize(
    ("paid_at", "expected"),
    [(BEFORE - timedelta(minutes=1), Decimal(1000)), (BEFORE, Decimal(1000)), (READ_AT, Decimal("1000.05"))],
)
def test_a_funding_payment_of_a_flow_explains_the_balance_only_after_the_previous_reading(
    paid_at: datetime, expected: Decimal
) -> None:
    flow = flow_on("BTC")
    funding = (FundingEntry(a_payment("BTC", Decimal("0.05"), paid_at=paid_at), flow.id),)

    result = reconcile(
        [flow], an_activity(balance=expected), booked_funding=funding, last=previous(reference=Decimal(1000))
    )

    assert result.comparison == BalanceComparison(expected, expected, READ_AT)
    assert result.items == ()


def test_the_executions_and_funding_of_no_flow_do_not_explain_the_balance() -> None:
    fill = a_fill("BTC", None, realized_pnl=Decimal(30))
    funding = (FundingEntry(a_payment("BTC", Decimal(5)), None),)

    result = reconcile(
        [flow_on("BTC")],
        an_activity(balance=Decimal(1035)),
        booked=(unattributed(fill),),
        booked_funding=funding,
        last=previous(reference=Decimal(1000)),
        threshold=Decimal(10),
    )

    assert result.comparison == BalanceComparison(Decimal(1000), Decimal(1035), READ_AT)


# ADR saldo-atteso-dalle-righe-del-registro-dopo-la-lettura-precedente: the rows another path recorded after the
# previous reading, a reversal or a cash out, explain the balance as well (Bug 633).
def test_the_rows_of_the_flows_in_the_ledger_after_the_previous_reading_explain_the_balance() -> None:
    flow = flow_on("BTC")
    closing = a_fill("BTC", uuid4(), realized_pnl=Decimal("4.6"), fee=Decimal("0.1"))
    funding = (FundingEntry(a_payment("BTC", Decimal("-0.5")), flow.id),)

    result = reconcile(
        [flow],
        an_activity(balance=Decimal(1004)),
        booked=(of_platform(closing, flow),),
        booked_funding=funding,
        last=previous(reference=Decimal(1000)),
    )

    assert result.comparison == BalanceComparison(Decimal(1004), Decimal(1004), READ_AT)
    assert result.items == ()


def test_a_row_of_the_ledger_after_this_reading_explains_the_next_one() -> None:
    flow = flow_on("BTC")
    later = a_fill("BTC", uuid4(), realized_pnl=Decimal(30), executed_at=READ_AT + timedelta(seconds=1))
    funding = (FundingEntry(a_payment("BTC", Decimal(5), paid_at=READ_AT + timedelta(seconds=1)), flow.id),)

    result = reconcile(
        [flow],
        an_activity(balance=Decimal(1000)),
        booked=(of_platform(later, flow),),
        booked_funding=funding,
        last=previous(reference=Decimal(1000)),
    )

    assert result.comparison == BalanceComparison(Decimal(1000), Decimal(1000), READ_AT)


def test_the_rows_just_recorded_explain_the_balance_only_through_the_ledger() -> None:
    flow = flow_on("BTC")
    fill = a_fill("BTC", uuid4(), realized_pnl=Decimal(30), fee=Decimal(2))

    result = reconcile(
        [flow],
        an_activity(balance=Decimal(1000)),
        recorded=(of_platform(fill, flow),),
        funding=(FundingEntry(a_payment("BTC", Decimal(5)), flow.id),),
        last=previous(reference=Decimal(1000)),
    )

    assert result.comparison == BalanceComparison(Decimal(1000), Decimal(1000), READ_AT)


def test_a_row_recorded_before_this_reconciliation_is_neither_an_unknown_fill_nor_a_closing_outside() -> None:
    flow = flow_on("BTC")
    fill = a_fill("BTC", None, fill_id="9", realized_pnl=Decimal(3), size=Decimal(-1), start_position=Decimal(1))

    result = reconcile(
        [flow],
        an_activity(balance=Decimal(1003)),
        booked=(LedgerEntry(fill, flow.id, ExecutionKind.OUTSIDE_CLOSING),),
        last=previous({flow.id: frozenset({"BTC"})}, reference=Decimal(1000)),
    )

    assert result.items == ()
    assert result.closed_outside == (OutsideClosing(flow.id, "BTC", Decimal(0), Decimal(0), READ_AT),)
    assert result.comparison == BalanceComparison(Decimal(1003), Decimal(1003), READ_AT)


def test_the_movements_in_the_ledger_after_the_last_reading_explain_the_balance() -> None:
    movements = (a_movement(Decimal(500), movement_id="0x1"), a_movement(Decimal(-300), moved_at=BEFORE))

    result = reconcile(
        [flow_on("BTC")],
        an_activity(balance=Decimal(1500)),
        booked_movements=movements,
        last=previous(reference=Decimal(1000)),
    )

    assert result.comparison == BalanceComparison(Decimal(1500), Decimal(1500), READ_AT)
    assert result.items == ()
    assert result.alarm is None


def test_a_movement_after_this_reading_is_left_to_the_next_one() -> None:
    later = a_movement(Decimal(500), movement_id="0x1", moved_at=READ_AT + timedelta(seconds=1))

    result = reconcile(
        [flow_on("BTC")],
        an_activity(balance=Decimal(1000)),
        booked_movements=(later,),
        last=previous(reference=Decimal(1000)),
    )

    assert result.comparison == BalanceComparison(Decimal(1000), Decimal(1000), READ_AT)


def test_a_deviation_within_the_threshold_is_an_unexplained_change_of_the_balance() -> None:
    result = reconcile([flow_on("BTC")], an_activity(balance=Decimal(995)), last=previous(reference=Decimal(1000)))

    assert result.items == (
        UnattributableItem(ACCOUNT, UnattributableKind.BALANCE_CHANGE, READ_AT.isoformat(), None, Decimal(-5), READ_AT),
    )
    assert result.alarm is None
    assert result.reading.reference_balance == Decimal(995)
    assert result.reading.comparison == BalanceComparison(Decimal(1000), Decimal(995), READ_AT)


def test_a_balance_as_expected_records_nothing() -> None:
    result = reconcile([flow_on("BTC")], an_activity(balance=Decimal(1000)), last=previous(reference=Decimal(1000)))

    assert result.items == ()
    assert result.alarm is None


def test_a_deviation_beyond_the_threshold_raises_an_alarm_and_keeps_the_expected_balance_as_reference() -> None:
    result = reconcile([flow_on("BTC")], an_activity(balance=Decimal(980)), last=previous(reference=Decimal(1000)))

    assert result.alarm == ReconciliationAlarm(ACCOUNT, Decimal(1000), Decimal(980), Decimal(2), READ_AT)
    assert result.items == ()
    assert result.reading.reference_balance == Decimal(1000)


def test_the_threshold_of_the_account_decides_the_alarm() -> None:
    result = reconcile(
        [flow_on("BTC")],
        an_activity(balance=Decimal(980)),
        last=previous(reference=Decimal(1000)),
        threshold=Decimal(3),
    )

    assert result.alarm is None


def test_a_confirmed_reading_takes_the_balance_read_as_reference() -> None:
    result = reconcile([flow_on("BTC")], an_activity(balance=Decimal(980)), last=previous(reference=Decimal(1000)))

    assert result.reading.confirmed().reference_balance == Decimal(980)


def test_a_reading_without_comparison_keeps_its_reference_when_confirmed() -> None:
    assert previous(reference=Decimal(1000)).confirmed().reference_balance == Decimal(1000)


# Bug 778, ADR riconciliazione-periodica-dei-conti-con-posizioni-aperte: the periodic check reads an account only when
# its flows held open positions at the last reading and the interval of the account has passed since.

INTERVAL = timedelta(minutes=5)


def test_a_reading_with_open_positions_is_due_once_the_interval_has_passed() -> None:
    reading = previous({FlowId.new(): frozenset({"BTC"})})

    assert reading.due_for_reconciliation(BEFORE + INTERVAL, INTERVAL)
    assert reading.due_for_reconciliation(BEFORE + INTERVAL * 2, INTERVAL)


def test_a_reading_with_open_positions_is_not_due_before_the_interval() -> None:
    reading = previous({FlowId.new(): frozenset({"BTC"})})

    assert not reading.due_for_reconciliation(BEFORE + INTERVAL - timedelta(seconds=1), INTERVAL)


def test_a_reading_without_open_positions_is_never_due() -> None:
    reading = previous({FlowId.new(): frozenset(), FlowId.new(): frozenset()})

    assert not reading.due_for_reconciliation(BEFORE + INTERVAL * 100, INTERVAL)
