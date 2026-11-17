from decimal import Decimal

from autotrading.application.notifications.notify_flow_event import NotifyFlowEventUseCase
from autotrading.domain.notifications.notification import Amount, Notification


class NotifyCashOutDoneUseCase:
    """Tells the user a cash-out of a flow was made, with the money it freed in the settlement currency (R3.5.1)."""

    def __init__(self, notifier: NotifyFlowEventUseCase, currency: str) -> None:
        self._notifier = notifier
        self._currency = currency

    def execute(self, flow_name: str, freed: Decimal) -> None:
        self._notifier.execute(Notification.cash_out_done(flow_name, Amount(freed, self._currency)))
