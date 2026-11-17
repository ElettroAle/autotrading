from decimal import Decimal
from uuid import UUID

from autotrading.application.notifications.ports import NotifierPort
from autotrading.domain.notifications.notification import Amount, Notification


class NotifyUnattributableMovementUseCase:
    """Tells the user the balance of the account changed with no flow behind it, in the settlement currency (R1.6.2)."""

    def __init__(self, notifier: NotifierPort, currency: str) -> None:
        self._notifier = notifier
        self._currency = currency

    def execute(self, account_id: UUID, account_name: str, amount: Decimal) -> None:
        self._notifier.execute(
            Notification.unattributable_movement(account_id, account_name, Amount(amount, self._currency))
        )
