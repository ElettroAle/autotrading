"""Closing a position for a flow: what happened, as data the flows context reads, never as an error (ADR 0085)."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from autotrading.application.orders.close_flow_position import (
    CloseFlowPositionCommand,
    CloseFlowPositionUseCase,
    ClosingReport,
)
from autotrading.application.orders.errors import (
    NoOpenPositionError,
    OrderAccountNotFoundError,
    OrderExchangeUnavailableError,
    OrderWorkerUnavailableError,
)
from autotrading.domain.orders.order import OrderStatus
from autotrading.domain.orders.order_outcome import OrderOutcome
from autotrading.domain.orders.rejection import RejectionReason
from autotrading.domain.tenancy.user_id import UserId

ACCOUNT = uuid4()
USER = UserId("oid-anna")
AT = datetime(2026, 11, 12, 9, 45, tzinfo=UTC)


class ScriptedClosing:
    def __init__(self, outcome: OrderOutcome | None = None, failure: Exception | None = None) -> None:
        self.outcome = outcome
        self.failure = failure
        self.calls: list[tuple[UUID, str, UserId]] = []

    def close(self, account_id: UUID, coin: str, user_id: UserId) -> OrderOutcome:
        self.calls.append((account_id, coin, user_id))
        if self.failure is not None:
            raise self.failure
        assert self.outcome is not None
        return self.outcome


def report_of(closing: ScriptedClosing) -> ClosingReport:
    return CloseFlowPositionUseCase(closing).execute(CloseFlowPositionCommand(ACCOUNT, "BTC", USER))


def test_an_executed_closing_reports_its_fill() -> None:
    outcome = OrderOutcome(
        uuid4(),
        OrderStatus.FILLED,
        "BTC",
        average_price=Decimal(102000),
        fee=Decimal("0.05"),
        realized_pnl=Decimal("1.5"),
        executed_at=AT,
    )
    closing = ScriptedClosing(outcome)

    report = report_of(closing)

    assert closing.calls == [(ACCOUNT, "BTC", USER)]
    assert report == ClosingReport(
        found=True, average_price=Decimal(102000), executed_at=AT, fee=Decimal("0.05"), realized_pnl=Decimal("1.5")
    )


def test_no_open_position_reports_nothing_found() -> None:
    assert report_of(ScriptedClosing(failure=NoOpenPositionError("BTC"))) == ClosingReport(found=False)


@pytest.mark.parametrize(
    "failure", [OrderAccountNotFoundError(), OrderExchangeUnavailableError(), OrderWorkerUnavailableError()]
)
def test_a_closing_that_cannot_be_sent_reports_the_reason(failure: Exception) -> None:
    assert report_of(ScriptedClosing(failure=failure)) == ClosingReport(found=True, refusal=str(failure))


def test_a_refused_closing_reports_the_message_of_the_exchange() -> None:
    outcome = OrderOutcome(uuid4(), OrderStatus.REJECTED, "BTC", exchange_message="Insufficient margin")

    assert report_of(ScriptedClosing(outcome)) == ClosingReport(found=True, refusal="Insufficient margin")


def test_a_refused_closing_without_message_reports_the_reason() -> None:
    outcome = OrderOutcome(uuid4(), OrderStatus.REJECTED, "BTC", reason=RejectionReason.INSUFFICIENT_MARGIN)

    assert report_of(ScriptedClosing(outcome)) == ClosingReport(
        found=True, refusal=str(RejectionReason.INSUFFICIENT_MARGIN)
    )


def test_a_closing_not_confirmed_in_time_reports_its_status() -> None:
    outcome = OrderOutcome(uuid4(), OrderStatus.UNKNOWN, "BTC", average_price=Decimal(1), executed_at=AT)

    assert report_of(ScriptedClosing(outcome)) == ClosingReport(found=True, refusal=OrderStatus.UNKNOWN.value)
