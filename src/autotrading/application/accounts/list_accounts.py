from collections.abc import Mapping

from autotrading.application.accounts.account_summary import AccountSummary
from autotrading.application.accounts.ports import AccountRepositoryPort, AllocatedCapitalPort, ExchangePort
from autotrading.application.accounts.verification import network_of


class ListAccountsUseCase:
    """The accounts of the tenant of the request, and only those (R0.1.3), with network and capital held (R2.2.1)."""

    def __init__(
        self,
        accounts: AccountRepositoryPort,
        capital: AllocatedCapitalPort,
        exchanges: Mapping[str, ExchangePort],
        currency: str,
    ) -> None:
        self._accounts = accounts
        self._capital = capital
        self._exchanges = exchanges
        self._currency = currency

    def execute(self) -> list[AccountSummary]:
        return [
            AccountSummary.of(
                account,
                self._capital.allocated_capital(account.id),
                network_of(self._exchanges, account.exchange),
                self._currency,
            )
            for account in self._accounts.list()
        ]
