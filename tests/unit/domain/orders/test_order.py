from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.errors import CycleOrderClosesFlowError
from autotrading.domain.orders.execution import Execution
from autotrading.domain.orders.flow_link import FlowLink
from autotrading.domain.orders.market_order import MarketOrder
from autotrading.domain.orders.order import Order, OrderOrigin, OrderRequest, OrderSource, OrderStatus
from autotrading.domain.orders.rejection import Rejection, RejectionReason
from autotrading.domain.orders.slippage import Slippage

AT = datetime(2026, 11, 10, tzinfo=UTC)
REQUEST = OrderRequest(
    uuid4(),
    OrderSource(OrderOrigin.MANUAL, "oid-anna"),
    2,
    MarketOrder.opening("BTC", Direction.LONG, Decimal("0.001"), Slippage.default()),
)


def execution(size: str) -> Execution:
    return Execution(Decimal(size), Decimal(100000), Decimal("0.045"), Decimal(0), AT)


def test_an_order_executed_for_the_whole_size_is_filled() -> None:
    order = Order.executed(REQUEST, execution("0.001"))

    assert order.status is OrderStatus.FILLED
    assert order.execution == execution("0.001")


def test_an_order_executed_for_part_of_the_size_is_partially_filled() -> None:
    assert Order.executed(REQUEST, execution("0.0006")).status is OrderStatus.PARTIALLY_FILLED


def test_a_rejected_order_keeps_the_rejection_and_no_execution() -> None:
    order = Order.rejected(REQUEST, Rejection.of("Insufficient margin"))

    assert order.status is OrderStatus.REJECTED
    assert order.execution is None
    assert order.rejection == Rejection(RejectionReason.INSUFFICIENT_MARGIN, "Insufficient margin")


def test_an_order_without_outcome_is_unknown() -> None:
    order = Order.unknown(REQUEST)

    assert order.status is OrderStatus.UNKNOWN
    assert (order.execution, order.rejection) == (None, None)


def test_the_identifier_of_an_order_is_the_one_sent() -> None:
    assert Order.unknown(REQUEST).id == REQUEST.market_order.id


def test_the_source_names_origin_and_user() -> None:
    assert Order.unknown(REQUEST).request.source == OrderSource(OrderOrigin.MANUAL, "oid-anna")


def test_a_closing_of_a_flow_belongs_to_the_flow_it_closes() -> None:
    flow_id = uuid4()

    source = OrderSource(OrderOrigin.MANUAL, "oid-anna", closing_flow_id=flow_id)

    assert source.flow_id == flow_id


def test_an_order_of_a_cycle_belongs_to_the_flow_of_its_cycle() -> None:
    link = FlowLink(uuid4(), AT, "BTC")

    assert OrderSource(OrderOrigin.FLOW, flow=link).flow_id == link.flow_id


def test_a_manual_command_belongs_to_no_flow() -> None:
    assert OrderSource(OrderOrigin.MANUAL, "oid-anna").flow_id is None


def test_an_order_cannot_come_from_a_cycle_and_close_a_flow_at_once() -> None:
    link = FlowLink(uuid4(), AT, "BTC")

    with pytest.raises(CycleOrderClosesFlowError) as raised:
        OrderSource(OrderOrigin.FLOW, flow=link, closing_flow_id=uuid4())

    assert str(raised.value) == "un ordine del ciclo non chiude un flusso fuori dal ciclo"
