from decimal import Decimal

from autotrading.application.notifications.notify_flow_event import NotifyFlowEventUseCase
from autotrading.domain.notifications.notification import Amount, Notification


class NotifyPositionClosedUseCase:
    """Tells the user a position of a flow closed, with its PnL in the currency the exchange settles in (ADR 0070) and,
    for a closing by a protection or a liquidation, its reason, in the one notification of the closing (R3.5.1).
    """

    def __init__(self, notifier: NotifyFlowEventUseCase, currency: str) -> None:
        self._notifier = notifier
        self._currency = currency

    def execute(self, flow_name: str, asset: str, pnl: Decimal, reason: str) -> None:
        self._notifier.execute(Notification.position_closed(flow_name, asset, Amount(pnl, self._currency), reason))
