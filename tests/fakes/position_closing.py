from collections.abc import Callable
from uuid import UUID

from autotrading.application.orders.close_exchange_position import (
    CloseExchangePositionCommand,
    CloseExchangePositionUseCase,
)
from autotrading.application.orders.errors import OrderWorkerUnavailableError
from autotrading.application.orders.outcome import OrderOutcome
from autotrading.domain.orders.order import OrderOrigin, OrderSource
from autotrading.domain.tenancy.user_id import UserId


class FakePositionClosingAdapter:
    """The worker reached in process instead of over HTTP: the same use case the worker runs, for the same tenant."""

    def __init__(self, worker: Callable[[], CloseExchangePositionUseCase]) -> None:
        self._worker = worker
        self.reachable = True

    def close(self, account_id: UUID, coin: str, user_id: UserId) -> OrderOutcome:
        if not self.reachable:
            raise OrderWorkerUnavailableError
        return OrderOutcome.of(
            self._worker().execute(
                CloseExchangePositionCommand(account_id, coin, OrderSource(OrderOrigin.MANUAL, user_id.value))
            )
        )
