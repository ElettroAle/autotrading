"""The bridge bootstrap builds to close the positions of a stopped flow (ADR 0055)."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from autotrading.application.orders.close_flow_position import CloseFlowPositionUseCase
from autotrading.application.orders.errors import (
    NoOpenPositionError,
    OrderAccountNotFoundError,
    OrderExchangeUnavailableError,
    OrderWorkerUnavailableError,
)
from autotrading.bootstrap import FlowPositionsFromOrders
from autotrading.domain.flows.stop_outcome import ClosingFill, PositionClosing
from autotrading.domain.orders.order import OrderStatus
from autotrading.domain.orders.order_outcome import OrderOutcome
from autotrading.domain.orders.rejection import RejectionReason
from autotrading.domain.tenancy.user_id import UserId

USER = UserId("oid-anna")
ACCOUNT = uuid4()


class ScriptedClosing:
    def __init__(self) -> None:
        self.outcome: OrderOutcome | None = None
        self.failure: Exception | None = None
        self.asked: list[tuple[UUID, str, UserId]] = []

    def close(self, account_id: UUID, coin: str, user_id: UserId) -> OrderOutcome:
        self.asked.append((account_id, coin, user_id))
        if self.failure is not None:
            raise self.failure
        assert self.outcome is not None
        return self.outcome


def an_outcome(status: OrderStatus, **values: object) -> OrderOutcome:
    return OrderOutcome(uuid4(), status, "BTC", **values)  # type: ignore[arg-type]  # each test names the values it reads


@pytest.fixture
def closing() -> ScriptedClosing:
    return ScriptedClosing()


@pytest.fixture
def positions(closing: ScriptedClosing) -> FlowPositionsFromOrders:
    return FlowPositionsFromOrders(CloseFlowPositionUseCase(closing))


EXECUTED = datetime(2026, 11, 12, 9, 45, tzinfo=UTC)
FILLED = {"average_price": Decimal(102000), "executed_at": EXECUTED, "fee": Decimal("0.05")}


@pytest.mark.parametrize("status", [OrderStatus.FILLED, OrderStatus.PARTIALLY_FILLED])
def test_a_closing_executed_gives_its_fill(
    positions: FlowPositionsFromOrders, closing: ScriptedClosing, status: OrderStatus
) -> None:
    closing.outcome = an_outcome(status, **FILLED)

    assert positions.close(ACCOUNT, "BTC", USER) == PositionClosing(
        "BTC", ClosingFill(Decimal(102000), EXECUTED, Decimal("0.05"))
    )
    assert closing.asked == [(ACCOUNT, "BTC", USER)]


@pytest.mark.parametrize("missing", ["average_price", "executed_at", "fee"])
def test_a_closing_not_confirmed_in_time_is_a_position_maybe_still_open(
    positions: FlowPositionsFromOrders, closing: ScriptedClosing, missing: str
) -> None:
    closing.outcome = an_outcome(OrderStatus.UNKNOWN, **{**FILLED, missing: None})

    assert positions.close(ACCOUNT, "BTC", USER) == PositionClosing("BTC", refusal=OrderStatus.UNKNOWN.value)


def test_a_closing_refused_gives_the_message_of_the_exchange(
    positions: FlowPositionsFromOrders, closing: ScriptedClosing
) -> None:
    closing.outcome = an_outcome(OrderStatus.REJECTED, reason=RejectionReason.OTHER, exchange_message="Order rejected")

    assert positions.close(ACCOUNT, "BTC", USER) == PositionClosing("BTC", refusal="Order rejected")


def test_a_closing_refused_without_a_message_gives_its_reason(
    positions: FlowPositionsFromOrders, closing: ScriptedClosing
) -> None:
    closing.outcome = an_outcome(OrderStatus.REJECTED, reason=RejectionReason.INSUFFICIENT_MARGIN)

    assert positions.close(ACCOUNT, "BTC", USER) == PositionClosing("BTC", refusal="margine insufficiente")


def test_no_position_on_the_asset_is_nothing_to_close(
    positions: FlowPositionsFromOrders, closing: ScriptedClosing
) -> None:
    closing.failure = NoOpenPositionError("BTC")

    assert positions.close(ACCOUNT, "BTC", USER) is None


@pytest.mark.parametrize(
    "failure", [OrderAccountNotFoundError(), OrderExchangeUnavailableError(), OrderWorkerUnavailableError()]
)
def test_a_closing_that_cannot_be_done_gives_the_reason(
    positions: FlowPositionsFromOrders, closing: ScriptedClosing, failure: Exception
) -> None:
    closing.failure = failure

    assert positions.close(ACCOUNT, "BTC", USER) == PositionClosing("BTC", refusal=str(failure))
