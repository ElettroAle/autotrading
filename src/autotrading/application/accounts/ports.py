from typing import Protocol

from autotrading.domain.accounts.account import Account
from autotrading.domain.accounts.account_id import AccountId
from autotrading.domain.accounts.account_name import AccountName
from autotrading.domain.accounts.account_state import AccountState
from autotrading.domain.accounts.credentials import Credentials
from autotrading.domain.accounts.removal import FlowPositionLeftOpen
from autotrading.domain.accounts.sealed_credentials import SealedCredentials
from autotrading.domain.tenancy.user_id import UserId


class ExchangePort(Protocol):
    def read_state(self, credentials: Credentials) -> AccountState:
        """Reads balance, margin and positions, proving the credentials work on the exchange.

        Raises ExchangeRejectedCredentialsError with the message of the exchange, or ExchangeUnavailableError.
        """
        ...


class CredentialSealerPort(Protocol):
    """Bound to the tenant of the request: the sealed text names tenant and account (ADR 0007)."""

    def seal(self, account_id: AccountId, credentials: Credentials) -> SealedCredentials: ...


class CredentialOpenerPort(Protocol):
    """Only in the worker, the one service holding the private key (ADR 0007)."""

    def open(self, account: Account) -> Credentials:
        """Raises CredentialsNotOpenedError when the sealed text names another tenant or account, or no key opens it."""
        ...


class AccountStatePort(Protocol):
    """Bound to the tenant of the request: the live state of one of its accounts, read where the private key is."""

    def read_state(self, account_id: AccountId) -> AccountState:
        """Raises the errors of ExchangePort, AccountNotFoundError, or WorkerUnavailableError."""
        ...


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

    def remove(self, account_id: AccountId) -> None:
        """Deletes the credentials and hides the account, keeping its history (ADR 0025).

        Raises AccountNotFoundError when the tenant has no such account, also when it was already removed.
        """
        ...


class AccountFlowsPort(Protocol):
    """Bound to the tenant of the request: the flows that run on an account (R1.1.8)."""

    def operating(self, account_id: AccountId) -> tuple[str, ...]:
        """The names of the flows of the account that are active or paused."""
        ...

    def stop(self, account_id: AccountId, user_id: UserId) -> tuple[FlowPositionLeftOpen, ...]:
        """Stops every active or paused flow of the account closing its positions (R1.1.5); those left open."""
        ...

    def archive(self, account_id: AccountId) -> None:
        """Archives every flow of the account not archived yet: all of them are stopped by now."""
        ...
