from decimal import Decimal
from uuid import uuid4

from autotrading.adapters.outbound.sqlalchemy.order_repository import _row_of
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.support.orders import EXECUTED_AT, a_flow_order, a_rejected_order, an_executed_order


def test_a_row_carries_request_source_and_execution_read_from_the_exchange() -> None:
    tenant_id, account_id = TenantId.new(), uuid4()
    order = an_executed_order(account_id)

    assert _row_of(order, tenant_id) == {
        "id": order.id.value,
        "tenant_id": tenant_id.value,
        "account_id": account_id,
        "origin": "MANUAL",
        "user_id": "oid-anna",
        "coin": "BTC",
        "direction": "long",
        "reduce_only": False,
        "leverage": 2,
        "requested_size": Decimal("0.0002"),
        "slippage": Decimal("0.05"),
        "status": "FILLED",
        "filled_size": Decimal("0.0002"),
        "average_price": Decimal("100030.5"),
        "fee": Decimal("0.009003"),
        "realized_pnl": Decimal("-0.25"),
        "executed_at": EXECUTED_AT,
        "rejection_reason": None,
        "exchange_message": None,
        "flow_id": None,
        "cycle_planned_at": None,
        "decision_asset": None,
    }


def test_a_row_of_a_rejected_order_carries_reason_and_original_message_without_execution() -> None:
    row = _row_of(a_rejected_order(uuid4()), TenantId.new())

    assert (row["status"], row["rejection_reason"], row["exchange_message"]) == (
        "REJECTED",
        "INSUFFICIENT_MARGIN",
        "Insufficient margin to place order. asset=0",
    )
    assert (row["origin"], row["user_id"]) == ("VERIFICATION", None)
    assert all(row[name] is None for name in ("filled_size", "average_price", "fee", "realized_pnl", "executed_at"))


def test_a_row_of_a_flow_order_carries_the_flow_the_cycle_and_the_decision() -> None:
    order = a_flow_order(uuid4())
    link = order.request.source.flow
    assert link is not None

    row = _row_of(order, TenantId.new())

    assert (row["origin"], row["flow_id"], row["cycle_planned_at"], row["decision_asset"]) == (
        "FLOW",
        link.flow_id,
        link.cycle_planned_at,
        "BTC",
    )
