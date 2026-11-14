from dataclasses import dataclass

from autotrading.application.accounts.account_summary import AccountSummary
from autotrading.application.accounts.errors import AccountNotFoundError
from autotrading.application.accounts.ports import AccountRepositoryPort, AllocatedCapitalPort
from autotrading.domain.accounts.account import Account
from autotrading.domain.accounts.account_id import AccountId
from autotrading.domain.accounts.exchange_network import ExchangeNetwork


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
    """One account of the tenant of the request (R0.1.3, R0.2.3), with network and allocated capital (R2.2.1)."""

    def __init__(
        self, accounts: AccountRepositoryPort, capital: AllocatedCapitalPort, environment: str, currency: str
    ) -> None:
        self._accounts = accounts
        self._capital = capital
        self._network = ExchangeNetwork.of_installation(environment)
        self._currency = currency

    def execute(self, command: GetAccountCommand) -> AccountSummary:
        account = find_account(self._accounts, command.account_id)
        return AccountSummary.of(account, self._capital.allocated_capital(account.id), self._network, self._currency)
