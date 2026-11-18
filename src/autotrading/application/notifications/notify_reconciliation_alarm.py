from decimal import Decimal
from uuid import UUID

from autotrading.application.notifications.ports import AlertRepositoryPort, NotifierPort
from autotrading.domain.notifications.alert import AlertCause
from autotrading.domain.notifications.notification import Amount, Notification


class NotifyReconciliationAlarmUseCase:
    """Opens the alert of an alarm on the balance of the account, then tells the user its openings are suspended, with
    both balances in the settlement currency (R3.3.1, R6.2.3).
    """

    def __init__(self, notifier: NotifierPort, alerts: AlertRepositoryPort, currency: str) -> None:
        self._notifier = notifier
        self._alerts = alerts
        self._currency = currency

    def execute(self, account_id: UUID, account_name: str, read_balance: Decimal, expected_balance: Decimal) -> None:
        read, expected = Amount(read_balance, self._currency), Amount(expected_balance, self._currency)
        alert_id = self._alerts.open(AlertCause.reconciliation_alarm(account_id, account_name, read, expected))
        self._notifier.execute(Notification.reconciliation_alarm(alert_id.value, account_name, read, expected))
