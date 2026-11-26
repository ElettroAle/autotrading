from decimal import Decimal
from uuid import uuid4

from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.held_position import HeldPosition
from autotrading.domain.orders.held_protections import HeldProtections
from autotrading.domain.orders.protection_kind import ProtectionKind
from autotrading.domain.orders.protection_order import ActiveProtection

POSITION = HeldPosition("BTC", Direction.SHORT, Decimal("0.5"), 2, Decimal(60000))
STOP = ActiveProtection("7", ProtectionKind.STOP_LOSS, Decimal(63000))
TARGET = ActiveProtection("8", ProtectionKind.TAKE_PROFIT, Decimal(54000))


def test_a_position_with_a_stop_loss_waiting_has_it() -> None:
    assert HeldProtections(POSITION, (TARGET, STOP)).has_stop_loss


def test_a_position_with_only_a_take_profit_waiting_has_no_stop_loss() -> None:
    assert not HeldProtections(POSITION, (TARGET,)).has_stop_loss


def test_the_protections_waiting_are_recorded_for_the_flow_on_the_asset_of_the_position() -> None:
    account_id, flow_id = uuid4(), uuid4()

    recorded = HeldProtections(POSITION, (STOP, TARGET)).recorded_for(account_id, flow_id)

    assert [
        (each.account_id, each.flow_id, each.asset, each.kind, each.trigger_price, each.exchange_order_id)
        for each in recorded
    ] == [
        (account_id, flow_id, "BTC", ProtectionKind.STOP_LOSS, Decimal(63000), "7"),
        (account_id, flow_id, "BTC", ProtectionKind.TAKE_PROFIT, Decimal(54000), "8"),
    ]


def test_each_protection_recorded_gets_a_client_order_id_of_its_own() -> None:
    recorded = HeldProtections(POSITION, (STOP, TARGET)).recorded_for(uuid4(), uuid4())

    assert len({each.client_order_id for each in recorded}) == len(recorded)


def test_a_position_without_protections_waiting_records_nothing() -> None:
    assert HeldProtections(POSITION, ()).recorded_for(uuid4(), uuid4()) == ()
