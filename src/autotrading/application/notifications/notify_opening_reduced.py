from decimal import Decimal

from autotrading.application.notifications.notify_flow_event import NotifyFlowEventUseCase
from autotrading.domain.notifications.notification import Amount, Notification


class NotifyOpeningReducedUseCase:
    """Tells the user the risk check reduced an opening of a flow, with the margin asked and the one approved in the
    settlement currency (R3.5.1).
    """

    def __init__(self, notifier: NotifyFlowEventUseCase, currency: str) -> None:
        self._notifier = notifier
        self._currency = currency

    def execute(self, flow_name: str, asset: str, requested_margin: Decimal, approved_margin: Decimal) -> None:
        requested, approved = Amount(requested_margin, self._currency), Amount(approved_margin, self._currency)
        self._notifier.execute(Notification.opening_reduced(flow_name, asset, requested, approved))
