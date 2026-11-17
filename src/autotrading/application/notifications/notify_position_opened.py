from decimal import Decimal
from uuid import UUID

from autotrading.application.notifications.notify_flow_event import NotifyFlowEventUseCase
from autotrading.domain.notifications.notification import Amount, Notification


class NotifyPositionOpenedUseCase:
    """Tells the user a flow opened a position, its value in the currency the exchange settles in (R1.8.2)."""

    def __init__(self, notifier: NotifyFlowEventUseCase, currency: str) -> None:
        self._notifier = notifier
        self._currency = currency

    def execute(  # noqa: PLR0913, PLR0917 - the signature of the port
        self, flow_id: UUID, flow_name: str, asset: str, direction: str, leverage: int, value: Decimal
    ) -> None:
        amount = Amount(value, self._currency)
        self._notifier.execute(Notification.position_opened(flow_id, flow_name, asset, direction, leverage, amount))
