"""The bridge that records in the history of a flow the positions a user closes by hand (ADR 0061)."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from autotrading.application.flows.record_manual_closing import RecordManualClosingCommand
from autotrading.application.orders.errors import NoOpenPositionError
from autotrading.bootstrap import ManualClosingsRecordedInFlows
from autotrading.domain.flows.stop_outcome import ClosingFill
from autotrading.domain.orders.order import OrderStatus
from autotrading.domain.orders.order_outcome import OrderOutcome
from autotrading.domain.tenancy.user_id import UserId

ACCOUNT = uuid4()
USER = UserId("oid-anna")
EXECUTED_AT = datetime(2026, 11, 12, 9, 45, tzinfo=UTC)
FILLED = OrderOutcome(
    uuid4(),
    OrderStatus.FILLED,
    "BTC",
    filled_size=Decimal("0.001"),
    average_price=Decimal(102000),
    fee=Decimal("0.05"),
    executed_at=EXECUTED_AT,
)


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


class RecordedClosings:
    def __init__(self) -> None:
        self.commands: list[RecordManualClosingCommand] = []

    def execute(self, command: RecordManualClosingCommand) -> None:
        self.commands.append(command)


def test_an_executed_closing_is_recorded_with_its_fill_and_the_outcome_goes_back_unchanged() -> None:
    closing, history = ScriptedClosing(FILLED), RecordedClosings()

    outcome = ManualClosingsRecordedInFlows(closing, history).close(ACCOUNT, "BTC", USER)

    assert outcome == FILLED
    assert closing.calls == [(ACCOUNT, "BTC", USER)]
    fill = ClosingFill(Decimal(102000), EXECUTED_AT, Decimal("0.05"))
    assert history.commands == [RecordManualClosingCommand(ACCOUNT, "BTC", fill)]


@pytest.mark.parametrize(
    "outcome",
    [
        OrderOutcome(uuid4(), OrderStatus.REJECTED, "BTC", exchange_message="Insufficient margin"),
        OrderOutcome(uuid4(), OrderStatus.UNKNOWN, "BTC"),
        OrderOutcome(uuid4(), OrderStatus.FILLED, "BTC", average_price=Decimal(1), executed_at=EXECUTED_AT),
        OrderOutcome(uuid4(), OrderStatus.FILLED, "BTC", average_price=Decimal(1), fee=Decimal(0)),
        OrderOutcome(uuid4(), OrderStatus.FILLED, "BTC", fee=Decimal(0), executed_at=EXECUTED_AT),
    ],
)
def test_a_closing_not_executed_or_not_confirmed_is_passed_on_without_a_fill(outcome: OrderOutcome) -> None:
    history = RecordedClosings()

    assert ManualClosingsRecordedInFlows(ScriptedClosing(outcome), history).close(ACCOUNT, "BTC", USER) == outcome
    assert history.commands == [RecordManualClosingCommand(ACCOUNT, "BTC", None)]


def test_a_closing_that_fails_enters_no_history() -> None:
    history = RecordedClosings()
    bridge = ManualClosingsRecordedInFlows(ScriptedClosing(failure=NoOpenPositionError("BTC")), history)

    with pytest.raises(NoOpenPositionError):
        bridge.close(ACCOUNT, "BTC", USER)

    assert history.commands == []
