from decimal import Decimal

from autotrading.application.notifications.ports import NotifierPort
from autotrading.domain.notifications.notification import Amount, Notification


class NotifyPositionClosedUseCase:
    """Tells the user a position of a flow closed, with its PnL in the currency the exchange settles in (ADR 0070)."""

    def __init__(self, notifier: NotifierPort, currency: str) -> None:
        self._notifier = notifier
        self._currency = currency

    def execute(self, flow_name: str, asset: str, pnl: Decimal) -> None:
        self._notifier.execute(Notification.position_closed(flow_name, asset, Amount(pnl, self._currency)))
