from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Connection, Engine, func, insert, select
from sqlalchemy.exc import IntegrityError

from autotrading.adapters.outbound.sqlalchemy.tables import accounts
from autotrading.application.accounts.errors import AccountNameInUseError
from autotrading.application.tenancy.errors import CrossTenantAccessError
from autotrading.domain.accounts.account import Account
from autotrading.domain.accounts.account_name import AccountName
from autotrading.domain.tenancy.tenant_id import TenantId

NAME_UNIQUE_IN_TENANT = "accounts_name_unique_in_tenant"


class SqlAlchemyAccountRepositoryAdapter:
    """Bound to the tenant of the request: every transaction declares it, and row level security does the rest."""

    def __init__(self, engine: Engine, tenant_id: TenantId) -> None:
        self._engine = engine
        self._tenant_id = tenant_id

    def name_in_use(self, name: AccountName) -> bool:
        query = select(func.count()).select_from(accounts).where(accounts.c.name == name.value)
        with self._transaction() as connection:
            return bool(connection.execute(query).scalar_one())

    def add(self, account: Account) -> None:
        self._require_own(account)
        try:
            with self._transaction() as connection:
                connection.execute(insert(accounts).values(_row_of(account)))
        except IntegrityError as error:
            if NAME_UNIQUE_IN_TENANT in str(error.orig):
                raise AccountNameInUseError(account.name) from error
            raise

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
        "credentials_key_version": account.credentials.key_version,
        "credentials_ciphertext": account.credentials.ciphertext,
    }
