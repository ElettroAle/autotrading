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

    def list(self) -> list[Account]: ...

    def get(self, account_id: AccountId) -> Account | None:
        """None both when the account does not exist and when it belongs to another tenant."""
        ...

    def replace(self, account: Account) -> None:
        """Saves the new state of an account of the tenant; raises CrossTenantAccessError for another tenant."""
        ...

    def add(self, account: Account) -> None:
        """Raises AccountNameInUseError when the tenant already has an account with that name."""
        ...
