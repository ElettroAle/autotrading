from collections.abc import Callable, Mapping
from datetime import datetime

from autotrading.application.accounts.account_summary import AccountSummary
from autotrading.application.accounts.key_expiry_details import KeyExpiryDetails
from autotrading.application.accounts.ports import AccountRepositoryPort, AllocatedCapitalPort, ExchangePort
from autotrading.application.accounts.verification import network_of, supported_exchange
from autotrading.domain.accounts.key_expiry import utc_day_of


class ListAccountsUseCase:
    """The accounts of the tenant of the request, and only those (R0.1.3), with network and capital held (R2.2.1) and
    the expiry of their credentials as of today (R6.2.2).
    """

    def __init__(
        self,
        accounts: AccountRepositoryPort,
        capital: AllocatedCapitalPort,
        exchanges: Mapping[str, ExchangePort],
        currency: str,
        clock: Callable[[], datetime],
    ) -> None:
        self._accounts = accounts
        self._capital = capital
        self._exchanges = exchanges
        self._currency = currency
        self._clock = clock

    def execute(self) -> list[AccountSummary]:
        today = utc_day_of(self._clock())
        return [
            AccountSummary.of(
                account,
                self._capital.allocated_capital(account.id),
                network_of(self._exchanges, account.exchange),
                self._currency,
                KeyExpiryDetails.of(account, supported_exchange(self._exchanges, account.exchange), today),
            )
            for account in self._accounts.list()
        ]
