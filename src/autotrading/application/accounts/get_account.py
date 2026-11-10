from dataclasses import dataclass

from autotrading.application.accounts.account_details import AccountDetails
from autotrading.application.accounts.errors import AccountNotFoundError
from autotrading.application.accounts.ports import AccountRepositoryPort
from autotrading.domain.accounts.account import Account
from autotrading.domain.accounts.account_id import AccountId


def find_account(accounts: AccountRepositoryPort, account_id: AccountId) -> Account:
    """An account of another tenant is answered exactly as one that does not exist (R0.1.3)."""
    account = accounts.get(account_id)
    if account is None:
        raise AccountNotFoundError
    return account


@dataclass(frozen=True, slots=True)
class GetAccountCommand:
    account_id: AccountId


class GetAccountUseCase:
    """The details of one account of the tenant of the request (R0.1.3, R0.2.3)."""

    def __init__(self, accounts: AccountRepositoryPort) -> None:
        self._accounts = accounts

    def execute(self, command: GetAccountCommand) -> AccountDetails:
        return AccountDetails.of(find_account(self._accounts, command.account_id))
