from autotrading.application.orders.close_exchange_position import (
    CloseExchangePositionCommand,
    CloseExchangePositionUseCase,
)
from autotrading.application.orders.order_failures import FailureNames, answered_or_named
from autotrading.application.orders.ports import VerificationClosingPort
from autotrading.domain.orders.order import OrderOrigin, OrderSource
from autotrading.domain.orders.order_outcome import OrderOutcome


class CloseVerificationPositionUseCase:
    """Closes the position of the procedure of verification, recorded with its origin and the user who launched it
    (R0.4.1, ADR 0024). Its failures carry the names the procedure gave them (ADR 0086).
    """

    def __init__(self, closing: CloseExchangePositionUseCase, failures: FailureNames) -> None:
        self._closing = closing
        self._failures = failures

    def execute(self, position: VerificationClosingPort) -> OrderOutcome:
        source = OrderSource(OrderOrigin.VERIFICATION, position.user_id.value)
        command = CloseExchangePositionCommand(position.account_id, position.coin, source)
        order = answered_or_named(
            lambda: self._closing.execute(command), self._failures.account_missing, self._failures.failed
        )
        return OrderOutcome.of(order)
