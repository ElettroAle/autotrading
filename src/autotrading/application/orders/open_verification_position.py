from autotrading.application.orders.open_position import OpenPositionCommand, OpenPositionUseCase
from autotrading.application.orders.order_failures import FailureNames, answered_or_named
from autotrading.application.orders.ports import VerificationOpeningPort
from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.order import OrderOrigin, OrderSource
from autotrading.domain.orders.order_outcome import OrderOutcome


class OpenVerificationPositionUseCase:
    """Opens the position of the procedure of verification, recorded with its origin and the user who launched it
    (R0.4.1, ADR 0024). Its failures carry the names the procedure gave them (ADR 0086).
    """

    def __init__(self, opening: OpenPositionUseCase, failures: FailureNames) -> None:
        self._opening = opening
        self._failures = failures

    def execute(self, opening: VerificationOpeningPort) -> OrderOutcome:
        command = OpenPositionCommand(
            account_id=opening.account_id,
            coin=opening.coin,
            direction=Direction(opening.side),
            leverage=opening.leverage,
            value=opening.value,
            source=OrderSource(OrderOrigin.VERIFICATION, opening.user_id.value),
        )
        order = answered_or_named(
            lambda: self._opening.execute(command), self._failures.account_missing, self._failures.failed
        )
        return OrderOutcome.of(order)
