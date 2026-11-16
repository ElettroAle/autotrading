from dataclasses import dataclass
from decimal import Decimal

from autotrading.application.accounts.get_account import find_account
from autotrading.application.accounts.ports import AccountRepositoryPort
from autotrading.domain.accounts.account_id import AccountId
from autotrading.domain.accounts.deviation_threshold import DeviationThreshold


@dataclass(frozen=True, slots=True)
class SetDeviationThresholdCommand:
    account_id: AccountId
    percent: Decimal


class SetDeviationThresholdUseCase:
    """Sets how far the balance of an account may go from the expected one before an alarm (R3.3.1).

    The next reconciliation of the account compares with the new threshold.
    """

    def __init__(self, accounts: AccountRepositoryPort) -> None:
        self._accounts = accounts

    def execute(self, command: SetDeviationThresholdCommand) -> DeviationThreshold:
        threshold = DeviationThreshold(command.percent)
        account = find_account(self._accounts, command.account_id)
        self._accounts.replace(account.with_deviation_threshold(threshold))
        return threshold
