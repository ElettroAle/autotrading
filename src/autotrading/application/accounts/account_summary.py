from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal

from autotrading.application.accounts.account_details import public_fields_of
from autotrading.application.accounts.key_expiry_details import KeyExpiryDetails
from autotrading.domain.accounts.account import Account
from autotrading.domain.accounts.account_id import AccountId
from autotrading.domain.accounts.account_name import AccountName
from autotrading.domain.accounts.declared_network import DeclaredNetwork
from autotrading.domain.accounts.exchange_name import ExchangeName


@dataclass(frozen=True, slots=True)
class AccountSummary:
    """An account as its owner reads it in the list (R2.2.1): network, the capital its flows hold, the public fields
    kept (Bug 401) and the expiry of its credentials (R6.2.2).

    The balance is not here: it comes from the exchange, which may not answer while the rest is still worth showing.
    """

    id: AccountId
    name: AccountName
    exchange: ExchangeName
    has_credentials: bool
    network: DeclaredNetwork
    allocated_capital: Decimal
    currency: str
    public_fields: Mapping[str, str]
    expiry: KeyExpiryDetails

    @classmethod
    def of(
        cls,
        account: Account,
        allocated_capital: Decimal,
        network: DeclaredNetwork,
        currency: str,
        expiry: KeyExpiryDetails,
    ) -> AccountSummary:
        return cls(
            account.id,
            account.name,
            account.exchange,
            has_credentials=bool(account.credentials.ciphertext),
            network=network,
            allocated_capital=allocated_capital,
            currency=currency,
            public_fields=public_fields_of(account),
            expiry=expiry,
        )
