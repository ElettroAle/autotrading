from typing import Protocol

from autotrading.domain.accounts.account import Account
from autotrading.domain.accounts.account_id import AccountId
from autotrading.domain.accounts.account_name import AccountName
from autotrading.domain.accounts.balance import Balance
from autotrading.domain.accounts.credentials import Credentials
from autotrading.domain.accounts.sealed_credentials import SealedCredentials


class ExchangePort(Protocol):
    def read_balance(self, credentials: Credentials) -> Balance:
        """Reads the balance proving the credentials work on the exchange.

        Raises ExchangeRejectedCredentialsError with the message of the exchange, or ExchangeUnavailableError.
        """
        ...


class CredentialSealerPort(Protocol):
    """Bound to the tenant of the request: the sealed text names tenant and account (ADR 0007)."""

    def seal(self, account_id: AccountId, credentials: Credentials) -> SealedCredentials: ...


class AccountRepositoryPort(Protocol):
    """Bound to the tenant of the request: it never sees the accounts of another tenant."""

    def name_in_use(self, name: AccountName) -> bool: ...

    def add(self, account: Account) -> None:
        """Raises AccountNameInUseError when the tenant already has an account with that name."""
        ...
