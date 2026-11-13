from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from autotrading.application.orders.close_position import ClosePositionCommand, ClosePositionUseCase
from autotrading.application.orders.errors import NoOpenPositionError
from autotrading.domain.orders.order import OrderStatus
from autotrading.domain.orders.order_outcome import OrderOutcome
from autotrading.domain.tenancy.user_id import UserId

ANNA = UserId("oid-anna")


class RecordingClosing:
    def __init__(self, outcome: OrderOutcome | None = None) -> None:
        self.requests: list[tuple[UUID, str, UserId]] = []
        self._outcome = outcome

    def close(self, account_id: UUID, coin: str, user_id: UserId) -> OrderOutcome:
        self.requests.append((account_id, coin, user_id))
        if self._outcome is not None:
            return self._outcome
        return OrderOutcome(uuid4(), OrderStatus.UNKNOWN, coin)


class RefusingClosing:
    def close(self, account_id: UUID, coin: str, user_id: UserId) -> OrderOutcome:  # noqa: ARG002 - no position anywhere
        raise NoOpenPositionError(coin)


class RecordedHistory:
    def __init__(self) -> None:
        self.closings: list[tuple[UUID, str, OrderOutcome]] = []

    def execute(self, account_id: UUID, asset: str, fill: OrderOutcome) -> None:
        self.closings.append((account_id, asset, fill))


def test_the_worker_is_asked_to_close_for_the_user_who_asked() -> None:
    closing, account_id = RecordingClosing(), uuid4()

    outcome = ClosePositionUseCase(closing, RecordedHistory()).execute(ClosePositionCommand(account_id, " BTC ", ANNA))

    assert closing.requests == [(account_id, "BTC", ANNA)]
    assert (outcome.status, outcome.coin) == (OrderStatus.UNKNOWN, "BTC")


def test_the_coin_keeps_its_case() -> None:
    closing = RecordingClosing()

    ClosePositionUseCase(closing, RecordedHistory()).execute(ClosePositionCommand(uuid4(), "kPEPE", ANNA))

    assert closing.requests[0][1] == "kPEPE"


def test_what_the_exchange_executed_enters_the_history_with_the_asset_asked() -> None:
    executed = OrderOutcome(uuid4(), OrderStatus.FILLED, "BTC", Decimal("0.01"), Decimal(64000), Decimal("0.3"))
    history, account_id = RecordedHistory(), uuid4()

    outcome = ClosePositionUseCase(RecordingClosing(executed), history).execute(
        ClosePositionCommand(account_id, " BTC ", ANNA)
    )

    assert history.closings == [(account_id, "BTC", executed)]
    assert outcome == executed


def test_a_closing_refused_before_any_order_enters_no_history() -> None:
    history = RecordedHistory()

    with pytest.raises(NoOpenPositionError):
        ClosePositionUseCase(RefusingClosing(), history).execute(ClosePositionCommand(uuid4(), "BTC", ANNA))

    assert history.closings == []
