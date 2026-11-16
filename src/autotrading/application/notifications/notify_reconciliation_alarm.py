from decimal import Decimal

from autotrading.application.notifications.ports import NotifierPort
from autotrading.domain.notifications.notification import Amount, Notification


class NotifyReconciliationAlarmUseCase:
    """Tells the user the balance of the account is not the expected one and its openings are suspended, with both
    balances in the settlement currency (R3.3.1).
    """

    def __init__(self, notifier: NotifierPort, currency: str) -> None:
        self._notifier = notifier
        self._currency = currency

    def execute(self, account_name: str, read_balance: Decimal, expected_balance: Decimal) -> None:
        read, expected = Amount(read_balance, self._currency), Amount(expected_balance, self._currency)
        self._notifier.execute(Notification.reconciliation_alarm(account_name, read, expected))
