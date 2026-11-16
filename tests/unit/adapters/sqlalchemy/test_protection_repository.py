from decimal import Decimal
from uuid import uuid4

import pytest

from autotrading.adapters.outbound.sqlalchemy.protection_repository import protection_of, row_of
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
