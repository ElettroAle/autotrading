from collections.abc import Sequence

from autotrading.application.flows.ports import FlowAccountNamePort, FlowNotifierPort
from autotrading.domain.flows.unattributable import UnattributableItem, UnattributableKind
from autotrading.domain.notifications.notification import Amount, Notification


class NotifyUnattributableUseCase:
    """Tells the user each new case of the account that no flow explains, with the name of the account (R1.6.2).

    A position closed outside is told by the history it enters (ADR 0070): only the new cases arrive here.
    """

    def __init__(self, accounts: FlowAccountNamePort, notifier: FlowNotifierPort, settlement_currency: str) -> None:
        self._accounts = accounts
        self._notifier = notifier
        self._settlement_currency = settlement_currency

    def execute(self, items: Sequence[UnattributableItem]) -> None:
        for item in items:
            self._notifier.execute(self._notification_of(item))

    def _notification_of(self, item: UnattributableItem) -> Notification:
        account = self._accounts.account_name(item.account_id)
        asset = item.asset or ""
        if item.kind is UnattributableKind.POSITION:
            return Notification.unattributable_position(account, asset)
        if item.kind is UnattributableKind.FILL:
            return Notification.unattributable_fill(account, asset)
        return Notification.unattributable_movement(account, Amount(item.amount, self._settlement_currency))
