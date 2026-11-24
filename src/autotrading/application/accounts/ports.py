from datetime import date
from decimal import Decimal
from typing import Protocol

from autotrading.domain.accounts.account import Account
from autotrading.domain.accounts.account_id import AccountId
from autotrading.domain.accounts.account_name import AccountName
from autotrading.domain.accounts.account_state import AccountState
from autotrading.domain.accounts.credential_field import CredentialField
from autotrading.domain.accounts.credentials import Credentials
from autotrading.domain.accounts.sealed_credentials import SealedCredentials
from autotrading.domain.accounts.virtual_balance import VirtualBalance


class ExchangePort(Protocol):
    def is_real(self) -> bool:
        """True when the adapter is configured on the network that moves real money (Bug 277)."""
        ...

    def network_name(self) -> str:
        """The name the exchange gives the network the adapter is configured on, as its users know it (R2.3.10)."""
        ...

    def credential_fields(self) -> tuple[CredentialField, ...]:
        """The data the exchange asks to operate an account, in the order the user gives them (R2.3.9)."""
        ...

    def read_state(self, credentials: Credentials) -> AccountState:
        """Reads balance, margin and positions, proving the credentials work on the exchange.

        Raises ExchangeRejectedCredentialsError with the message of the exchange, or ExchangeUnavailableError.
        """
        ...

    def reads_credential_expiry(self) -> bool:
        """True when the exchange tells until when credentials work: then the user never gives the date (R6.2.2)."""
        ...

    def credential_expiry(self, credentials: Credentials) -> date | None:
        """The day, in UTC, the credentials stop working as the exchange tells it; none when it tells none for them.

        Raises ExchangeRejectedCredentialsError with the message of the exchange, or ExchangeUnavailableError.
        """
        ...


class VirtualBalancePort(Protocol):
    """The virtual balance of the accounts of the tenant on an exchange that holds one instead of funds (R6.3.2), bound
    to the tenant of the request like every port of owned data.
    """

    def open(self, account_id: AccountId, balance: VirtualBalance) -> None:
        """The account starts from the balance, with nothing open."""
        ...

    def reset(self, account_id: AccountId, balance: VirtualBalance) -> None:
        """Every position of the account closed and every order cancelled, then the balance brought to the one given.

        Raises AccountNotFoundError for an account the exchange does not hold for the tenant.
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


class AllocatedCapitalPort(Protocol):
    """Bound to the tenant of the request: the capital its flows hold on one of its accounts (R2.2.1, ADR 0126)."""

    def allocated_capital(self, account_id: AccountId) -> Decimal:
        """The sum over its flows not archived: zero for an account without them, or of another tenant."""
        ...
