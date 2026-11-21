from collections.abc import Callable
from uuid import UUID

from autotrading.application.orders.close_exchange_position import (
    CloseExchangePositionCommand,
    CloseExchangePositionUseCase,
)
from autotrading.application.orders.errors import OrderWorkerUnavailableError
from autotrading.domain.orders.order import OrderOrigin, OrderSource
from autotrading.domain.orders.order_outcome import OrderOutcome
from autotrading.domain.tenancy.user_id import UserId


class FakePositionClosingAdapter:
    """The worker reached in process instead of over HTTP: the same use case the worker runs, for the same tenant."""

    def __init__(self, worker: Callable[[], CloseExchangePositionUseCase]) -> None:
        self._worker = worker
        self.reachable = True

    def close(self, account_id: UUID, coin: str, user_id: UserId, flow_id: UUID | None) -> OrderOutcome:
        if not self.reachable:
            raise OrderWorkerUnavailableError
        source = OrderSource(OrderOrigin.MANUAL, user_id.value, closing_flow_id=flow_id)
        return OrderOutcome.of(self._worker().execute(CloseExchangePositionCommand(account_id, coin, source)))
