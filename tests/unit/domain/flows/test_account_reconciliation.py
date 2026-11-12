from datetime import timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from autotrading.domain.flows.account_activity import AccountActivity
from autotrading.domain.flows.account_reconciliation import (
    OUTSIDE_PLATFORM,
    AccountReading,
    AccountReconciliation,
    OutsideClosing,
)
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.flows.unattributable import UnattributableItem, UnattributableKind
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.support.activity import READ_AT, a_fill, a_movement, a_position, an_activity
from tests.support.flows import a_configuration, a_flow

TENANT = TenantId(uuid4())
ACCOUNT = uuid4()
BEFORE = READ_AT - timedelta(minutes=5)
EARLIER = READ_AT - timedelta(minutes=10)


def flow_on(*assets: str, status: FlowStatus = FlowStatus.ACTIVE) -> Flow:
    return a_flow(TENANT, account_id=ACCOUNT, status=status, configuration=a_configuration(assets=assets))


def previous(open_assets: dict[FlowId, frozenset[str]] | None = None) -> AccountReading:
    return AccountReading(ACCOUNT, BEFORE, open_assets or {})


def reconcile(
    flows: list[Flow],
    activity: AccountActivity | None = None,
    *,
    orders: dict[UUID, FlowId | None] | None = None,
    last: AccountReading | None = None,
) -> AccountReconciliation:
    return AccountReconciliation.of(ACCOUNT, flows, activity or an_activity(), orders or {}, last)


def test_a_position_on_an_asset_of_no_flow_is_unattributable() -> None:
    activity = an_activity(positions=(a_position("BTC"), a_position("SOL", size=Decimal(3))))

    result = reconcile([flow_on("BTC")], activity)

    assert result.items == (
        UnattributableItem(ACCOUNT, UnattributableKind.POSITION, "SOL", "SOL", Decimal(3), READ_AT),
    )


def test_an_archived_flow_owns_no_asset_any_more() -> None:
    result = reconcile([flow_on("SOL", status=FlowStatus.ARCHIVED)], an_activity(positions=(a_position("SOL"),)))

    assert [item.reference for item in result.items] == ["SOL"]


def test_a_fill_without_an_order_of_the_platform_after_the_last_reading_is_unattributable() -> None:
    fill = a_fill("BTC", None, fill_id="77", executed_at=READ_AT)

    result = reconcile([flow_on("BTC")], an_activity(fills=(fill,)), last=previous())

    assert result.items == (UnattributableItem(ACCOUNT, UnattributableKind.FILL, "77", "BTC", Decimal(1), READ_AT),)


def test_a_fill_of_an_order_unknown_to_the_platform_is_unattributable() -> None:
    result = reconcile([flow_on("BTC")], an_activity(fills=(a_fill("BTC", uuid4()),)), last=previous())

    assert [item.kind for item in result.items] == [UnattributableKind.FILL]


def test_a_fill_of_an_order_of_the_platform_is_explained_even_without_a_flow() -> None:
    manual = uuid4()
    fills = (a_fill("BTC", manual, fill_id="1"), a_fill("BTC", None, fill_id="2", executed_at=BEFORE))

    result = reconcile([flow_on("BTC")], an_activity(fills=fills), orders={manual: None}, last=previous())

    assert result.items == ()


def test_without_a_previous_reading_the_past_fills_and_movements_are_the_starting_point() -> None:
    activity = an_activity(fills=(a_fill("BTC", None),), movements=(a_movement(Decimal(200)),))

    result = reconcile([flow_on("BTC")], activity)

    assert result.items == ()
    assert result.closed_outside == ()


def test_a_movement_of_the_balance_after_the_last_reading_is_unattributable() -> None:
    movements = (
        a_movement(Decimal(200), movement_id="0x1"),
        a_movement(Decimal(-5), moved_at=BEFORE, movement_id="0x2"),
    )

    result = reconcile([flow_on("BTC")], an_activity(movements=movements), last=previous())

    assert result.items == (
        UnattributableItem(ACCOUNT, UnattributableKind.BALANCE_CHANGE, "0x1", None, Decimal(200), READ_AT),
    )


def test_a_position_of_a_flow_gone_from_the_exchange_was_closed_outside_the_platform() -> None:
    flow = flow_on("BTC")
    fills = (
        a_fill("BTC", None, realized_pnl=Decimal(-30), fee=Decimal(1), executed_at=READ_AT - timedelta(minutes=2)),
        a_fill("BTC", None, realized_pnl=Decimal(-20), fee=Decimal(1), executed_at=READ_AT - timedelta(minutes=1)),
        a_fill("BTC", None, realized_pnl=Decimal(-99), fee=Decimal(9), executed_at=EARLIER),
        a_fill("ETH", None, realized_pnl=Decimal(-99), fee=Decimal(9), executed_at=READ_AT),
    )

    result = reconcile([flow], an_activity(fills=fills), last=previous({flow.id: frozenset({"BTC"})}))

    assert result.closed_outside == (
        OutsideClosing(flow.id, "BTC", OUTSIDE_PLATFORM, Decimal(-50), Decimal(2), READ_AT - timedelta(minutes=1)),
    )


def test_a_position_closed_outside_without_fills_closes_at_the_reading() -> None:
    flow = flow_on("BTC")

    result = reconcile([flow], last=previous({flow.id: frozenset({"BTC"})}))

    assert result.closed_outside == (OutsideClosing(flow.id, "BTC", OUTSIDE_PLATFORM, Decimal(0), Decimal(0), READ_AT),)


def test_the_outcome_of_a_closing_outside_ignores_the_fills_of_platform_orders() -> None:
    flow, manual = flow_on("BTC"), uuid4()
    fills = (a_fill("BTC", manual, realized_pnl=Decimal(5)), a_fill("BTC", None, realized_pnl=Decimal(-7)))

    result = reconcile(
        [flow], an_activity(fills=fills), orders={manual: None}, last=previous({flow.id: frozenset({"BTC"})})
    )

    assert [closing.realized_pnl for closing in result.closed_outside] == [Decimal(-7)]


def test_a_position_the_flow_closed_with_its_own_order_is_not_closed_outside() -> None:
    flow, order = flow_on("BTC"), uuid4()

    result = reconcile(
        [flow],
        an_activity(fills=(a_fill("BTC", order),)),
        orders={order: flow.id},
        last=previous({flow.id: frozenset({"BTC"})}),
    )

    assert result.closed_outside == ()


def test_an_order_of_the_flow_on_another_asset_does_not_explain_a_closing() -> None:
    flow, order = flow_on("BTC", "SOL"), uuid4()

    result = reconcile(
        [flow],
        an_activity(fills=(a_fill("SOL", order),)),
        orders={order: flow.id},
        last=previous({flow.id: frozenset({"BTC"})}),
    )

    assert [closing.asset for closing in result.closed_outside] == ["BTC"]


def test_an_order_of_the_flow_before_the_last_reading_does_not_explain_a_closing() -> None:
    flow, order = flow_on("BTC"), uuid4()

    result = reconcile(
        [flow],
        an_activity(fills=(a_fill("BTC", order, executed_at=BEFORE),)),
        orders={order: flow.id},
        last=previous({flow.id: frozenset({"BTC"})}),
    )

    assert [closing.asset for closing in result.closed_outside] == ["BTC"]


def test_an_order_of_another_flow_does_not_explain_a_closing() -> None:
    flow, other, order = flow_on("BTC"), flow_on("ETH"), uuid4()

    result = reconcile(
        [flow, other],
        an_activity(fills=(a_fill("BTC", order),)),
        orders={order: other.id},
        last=previous({flow.id: frozenset({"BTC"})}),
    )

    assert [closing.asset for closing in result.closed_outside] == ["BTC"]


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

    assert result.reading == AccountReading(ACCOUNT, READ_AT, {alfa.id: frozenset({"BTC"}), beta.id: frozenset()})


def test_the_assets_open_on_the_account_are_those_of_the_reading() -> None:
    result = reconcile([flow_on("BTC")], an_activity(positions=(a_position("BTC"), a_position("SOL"))))

    assert result.open_assets == frozenset({"BTC", "SOL"})
