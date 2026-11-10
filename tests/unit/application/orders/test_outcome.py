from uuid import uuid4

from autotrading.application.orders.outcome import OrderOutcome
from autotrading.domain.orders.order import Order, OrderStatus
from autotrading.domain.orders.rejection import RejectionReason
from tests.support.orders import EXECUTION, a_rejected_order, a_request, an_executed_order


def test_an_executed_order_shows_what_the_exchange_executed() -> None:
    order = an_executed_order(uuid4())

    outcome = OrderOutcome.of(order)

    assert outcome == OrderOutcome(
        order.id.value,
        OrderStatus.FILLED,
        "BTC",
        filled_size=EXECUTION.filled_size,
        average_price=EXECUTION.average_price,
        fee=EXECUTION.fee,
        realized_pnl=EXECUTION.realized_pnl,
        executed_at=EXECUTION.executed_at,
    )


def test_a_rejected_order_shows_reason_and_original_message() -> None:
    outcome = OrderOutcome.of(a_rejected_order(uuid4()))

    assert (outcome.status, outcome.reason) == (OrderStatus.REJECTED, RejectionReason.INSUFFICIENT_MARGIN)
    assert outcome.exchange_message == "Insufficient margin to place order. asset=0"
    assert outcome.filled_size is None


def test_an_order_without_outcome_shows_only_its_status() -> None:
    order = Order.unknown(a_request(uuid4()))

    assert OrderOutcome.of(order) == OrderOutcome(order.id.value, OrderStatus.UNKNOWN, "BTC")
