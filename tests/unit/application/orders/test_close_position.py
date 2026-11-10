from uuid import UUID, uuid4

from autotrading.application.orders.close_position import ClosePositionCommand, ClosePositionUseCase
from autotrading.application.orders.outcome import OrderOutcome
from autotrading.domain.orders.order import OrderStatus
from autotrading.domain.tenancy.user_id import UserId

ANNA = UserId("oid-anna")


class RecordingClosing:
    def __init__(self) -> None:
        self.requests: list[tuple[UUID, str, UserId]] = []

    def close(self, account_id: UUID, coin: str, user_id: UserId) -> OrderOutcome:
        self.requests.append((account_id, coin, user_id))
        return OrderOutcome(uuid4(), OrderStatus.UNKNOWN, coin)


def test_the_worker_is_asked_to_close_for_the_user_who_asked() -> None:
    closing, account_id = RecordingClosing(), uuid4()

    outcome = ClosePositionUseCase(closing).execute(ClosePositionCommand(account_id, " BTC ", ANNA))

    assert closing.requests == [(account_id, "BTC", ANNA)]
    assert (outcome.status, outcome.coin) == (OrderStatus.UNKNOWN, "BTC")


def test_the_coin_keeps_its_case() -> None:
    closing = RecordingClosing()

    ClosePositionUseCase(closing).execute(ClosePositionCommand(uuid4(), "kPEPE", ANNA))

    assert closing.requests[0][1] == "kPEPE"
