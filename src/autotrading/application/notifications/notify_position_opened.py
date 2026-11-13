from decimal import Decimal

from autotrading.application.notifications.ports import NotifierPort
from autotrading.domain.notifications.notification import Amount, Notification


class NotifyPositionOpenedUseCase:
    """Tells the user a flow opened a position, its value in the currency the exchange settles in (R1.8.2)."""

    def __init__(self, notifier: NotifierPort, currency: str) -> None:
        self._notifier = notifier
        self._currency = currency

    def execute(self, flow_name: str, asset: str, direction: str, leverage: int, value: Decimal) -> None:
        amount = Amount(value, self._currency)
        self._notifier.execute(Notification.position_opened(flow_name, asset, direction, leverage, amount))
