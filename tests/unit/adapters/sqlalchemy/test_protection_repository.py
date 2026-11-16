from decimal import Decimal
from uuid import uuid4

import pytest

from autotrading.adapters.outbound.sqlalchemy.flow_protection_levels import levels_of
from autotrading.adapters.outbound.sqlalchemy.protection_repository import protection_of, row_of
from autotrading.domain.flows.exit_plan import PlacedLevels
from autotrading.domain.orders.client_order_id import ClientOrderId
from autotrading.domain.orders.placed_protection import PlacedProtection
from autotrading.domain.orders.protection_kind import ProtectionKind


@pytest.mark.parametrize(
    ("kind", "name"), [(ProtectionKind.STOP_LOSS, "stop_loss"), (ProtectionKind.TAKE_PROFIT, "take_profit")]
)
def test_a_protection_is_saved_with_its_kind_by_name_and_reads_back_whole(kind: ProtectionKind, name: str) -> None:
    protection = PlacedProtection(uuid4(), uuid4(), "BTC", kind, Decimal("57000.5"), "4242", ClientOrderId.new())

    row = row_of(protection)

    assert row == {
        "client_order_id": protection.client_order_id.value,
        "account_id": protection.account_id,
        "flow_id": protection.flow_id,
        "asset": "BTC",
        "kind": name,
        "trigger_price": Decimal("57000.5"),
        "exchange_order_id": "4242",
    }
    assert protection_of(row) == protection


def test_the_levels_in_force_are_the_prices_of_the_stop_loss_and_of_the_take_profit() -> None:
    account_id, flow_id = uuid4(), uuid4()
    stop = PlacedProtection(
        account_id, flow_id, "BTC", ProtectionKind.STOP_LOSS, Decimal(62000), "1", ClientOrderId.new()
    )
    take_profit = PlacedProtection(
        account_id, flow_id, "BTC", ProtectionKind.TAKE_PROFIT, Decimal(68000), "2", ClientOrderId.new()
    )

    assert levels_of((stop, take_profit)) == PlacedLevels(Decimal(62000), Decimal(68000))
    assert levels_of((stop,)) == PlacedLevels(Decimal(62000), None)
    assert levels_of(()) == PlacedLevels(None, None)
