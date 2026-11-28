from dataclasses import dataclass

from autotrading.application.accounts.get_account import find_account
from autotrading.application.accounts.ports import AccountRepositoryPort
from autotrading.domain.accounts.account_id import AccountId
from autotrading.domain.accounts.reconciliation_interval import ReconciliationInterval


@dataclass(frozen=True, slots=True)
class SetReconciliationIntervalCommand:
    account_id: AccountId
    minutes: int


class SetReconciliationIntervalUseCase:
    """Sets how often, in minutes, the periodic check reconciles the account while its flows hold open positions (Bug
    778, ADR intervallo-di-riconciliazione-del-conto).

    The next check of the account waits for the new interval.
    """

    def __init__(self, accounts: AccountRepositoryPort) -> None:
        self._accounts = accounts

    def execute(self, command: SetReconciliationIntervalCommand) -> None:
        interval = ReconciliationInterval(command.minutes)
        account = find_account(self._accounts, command.account_id)
        self._accounts.replace(account.with_reconciliation_interval(interval))
