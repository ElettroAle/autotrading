from datetime import datetime
from decimal import Decimal
from uuid import UUID

from autotrading.application.notifications.notify_flow_event import NotifyFlowEventUseCase
from autotrading.domain.notifications.notification import Amount, Notification


class NotifyPositionClosedUseCase:
    """Tells the user a position of a flow closed, with its PnL in the currency the exchange settles in (ADR 0070) and,
    for a closing by a protection or a liquidation, its reason, in the one notification of the closing (R3.5.1); it
    leads to the closed position by its asset and the instant it closed (R3.5.6).
    """

    def __init__(self, notifier: NotifyFlowEventUseCase, currency: str) -> None:
        self._notifier = notifier
        self._currency = currency

    def execute(  # noqa: PLR0913, PLR0917 - the signature of the port
        self, flow_id: UUID, flow_name: str, asset: str, pnl: Decimal, reason: str, closed_at: datetime
    ) -> None:
        amount = Amount(pnl, self._currency)
        self._notifier.execute(Notification.position_closed(flow_id, flow_name, asset, amount, reason, closed_at))
