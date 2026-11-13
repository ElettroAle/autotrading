from collections.abc import Iterator
from contextlib import contextmanager
from uuid import UUID

from sqlalchemy import Connection, Engine, RowMapping, func, insert, select, update
from sqlalchemy.exc import IntegrityError

from autotrading.adapters.outbound.sqlalchemy.tables import accounts
from autotrading.application.accounts.errors import AccountNameInUseError
from autotrading.application.flows.errors import AccountToRemoveNotFoundError, FlowAccountNotFoundError
from autotrading.application.orders.errors import OrderAccountNotFoundError
from autotrading.application.tenancy.errors import CrossTenantAccessError
from autotrading.application.verification.errors import VerificationAccountNotFoundError
from autotrading.domain.accounts.account import Account
from autotrading.domain.accounts.account_id import AccountId
from autotrading.domain.accounts.account_name import AccountName
from autotrading.domain.accounts.exchange_account import ExchangeAccount
from autotrading.domain.accounts.exchange_name import ExchangeName
from autotrading.domain.accounts.sealed_credentials import SealedCredentials
from autotrading.domain.flows.sealed_address import SealedAddress
from autotrading.domain.orders.sealed_access import SealedAccess
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.verification.verification_access import SealedVerificationAccess

NAME_UNIQUE_IN_TENANT = "accounts_name_unique_in_tenant"
# A removed account keeps its row for the history and is invisible to every other query (ADR 0025).
IN_USE = accounts.c.removed_at.is_(None)


class SqlAlchemyAccountRepositoryAdapter:
    """Bound to the tenant of the request: every transaction declares it, and row level security does the rest."""

    def __init__(self, engine: Engine, tenant_id: TenantId) -> None:
        self._engine = engine
        self._tenant_id = tenant_id

    def name_in_use(self, name: AccountName) -> bool:
        query = select(func.count()).select_from(accounts).where(IN_USE, accounts.c.name == name.value)
        with self._transaction() as connection:
            return bool(connection.execute(query).scalar_one())

    def list(self) -> list[Account]:
        query = select(accounts).where(IN_USE).order_by(accounts.c.name)
        with self._transaction() as connection:
            return [_account_of(row) for row in connection.execute(query).mappings()]

    def get(self, account_id: AccountId) -> Account | None:
        query = select(accounts).where(IN_USE, accounts.c.id == account_id.value)
        with self._transaction() as connection:
            row = connection.execute(query).mappings().one_or_none()
        return None if row is None else _account_of(row)

    def sealed_access(self, account_id: UUID) -> SealedAccess:
        """The account as the orders context opens it to sign its orders (ADR 0023)."""
        account = self.get(AccountId(account_id))
        if account is None:
            raise OrderAccountNotFoundError
        sealed = account.credentials
        return SealedAccess(
            account.tenant_id, account_id, account.exchange.value, sealed.key_version, sealed.ciphertext
        )

    def sealed_address(self, account_id: UUID) -> SealedAddress:
        """The account as the flows context opens it to read it on its exchange (ADR 0044)."""
        account = self.get(AccountId(account_id))
        if account is None:
            raise FlowAccountNotFoundError
        sealed = account.credentials
        return SealedAddress(
            account.tenant_id, account_id, account.exchange.value, sealed.key_version, sealed.ciphertext
        )

    def sealed_verification(self, account_id: UUID) -> SealedVerificationAccess:
        """The account as the verification procedure opens it to read it on its exchange (ADR 0024)."""
        account = self.get(AccountId(account_id))
        if account is None:
            raise VerificationAccountNotFoundError
        sealed = account.credentials
        return SealedVerificationAccess(
            account.tenant_id, account_id, account.exchange.value, sealed.key_version, sealed.ciphertext
        )

    def exchange_of(self, account_id: UUID) -> str:
        """The exchange of an account as a flow sees it (ADR 0087): one the tenant does not have is not found."""
        account = self.get(AccountId(account_id))
        if account is None:
            raise FlowAccountNotFoundError
        return account.exchange.value

    def add(self, account: Account) -> None:
        self._require_own(account)
        try:
            with self._transaction() as connection:
                connection.execute(insert(accounts).values(_row_of(account)))
        except IntegrityError as error:
            if NAME_UNIQUE_IN_TENANT in str(error.orig):
                raise AccountNameInUseError(account.name) from error
            raise

    def replace(self, account: Account) -> None:
        self._require_own(account)
        statement = update(accounts).where(IN_USE, accounts.c.id == account.id.value).values(_row_of(account))
        with self._transaction() as connection:
            # Row level security hides the rows of other tenants: an account of theirs updates nothing.
            if connection.execute(statement).rowcount != 1:
                raise CrossTenantAccessError

    def has_account(self, account_id: UUID) -> bool:
        return self.get(AccountId(account_id)) is not None

    def remove_account(self, account_id: UUID) -> None:
        """The removal of an account as the flows context asks it (ADR 0090): credentials deleted, history kept."""
        statement = (
            update(accounts)
            .where(IN_USE, accounts.c.id == account_id)
            .values(removed_at=func.now(), credentials_key_version=None, credentials_ciphertext=None)
        )
        with self._transaction() as connection:
            # Row level security hides the rows of other tenants: an account of theirs is not found.
            if connection.execute(statement).rowcount != 1:
                raise AccountToRemoveNotFoundError

    def _require_own(self, account: Account) -> None:
        if account.tenant_id != self._tenant_id:
            raise CrossTenantAccessError

    @contextmanager
    def _transaction(self) -> Iterator[Connection]:
        with self._engine.begin() as connection:
            # Local to the transaction: a pooled connection never carries the tenant of a previous request.
            connection.execute(select(func.set_config("app.tenant_id", str(self._tenant_id.value), True)))
            yield connection


def _row_of(account: Account) -> dict[str, object]:
    return {
        "id": account.id.value,
        "tenant_id": account.tenant_id.value,
        "name": account.name.value,
        "exchange": account.exchange.value,
        "exchange_account_fingerprint": account.exchange_account.fingerprint,
        "credentials_key_version": account.credentials.key_version,
        "credentials_ciphertext": account.credentials.ciphertext,
    }


def _account_of(row: RowMapping) -> Account:
    return Account(
        AccountId(row["id"]),
        TenantId(row["tenant_id"]),
        AccountName(row["name"]),
        ExchangeName(row["exchange"]),
        ExchangeAccount(row["exchange_account_fingerprint"]),
        SealedCredentials(row["credentials_key_version"], row["credentials_ciphertext"]),
    )
