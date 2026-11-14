from dataclasses import dataclass
from decimal import Decimal

from autotrading.domain.accounts.account import Account
from autotrading.domain.accounts.account_id import AccountId
from autotrading.domain.accounts.account_name import AccountName
from autotrading.domain.accounts.exchange_name import ExchangeName
from autotrading.domain.accounts.exchange_network import ExchangeNetwork


@dataclass(frozen=True, slots=True)
class AccountSummary:
    """An account as its owner reads it in the list (R2.2.1): network and the capital its flows hold.

    The balance is not here: it comes from the exchange, which may not answer while the rest is still worth showing.
    """

    id: AccountId
    name: AccountName
    exchange: ExchangeName
    has_credentials: bool
    network: ExchangeNetwork
    allocated_capital: Decimal
    currency: str

    @classmethod
    def of(
        cls, account: Account, allocated_capital: Decimal, network: ExchangeNetwork, currency: str
    ) -> AccountSummary:
        return cls(
            account.id,
            account.name,
            account.exchange,
            has_credentials=bool(account.credentials.ciphertext),
            network=network,
            allocated_capital=allocated_capital,
            currency=currency,
        )
