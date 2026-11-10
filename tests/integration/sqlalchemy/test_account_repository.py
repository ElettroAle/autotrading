from uuid import uuid4

import pytest
from sqlalchemy import Engine, func, select, text
from sqlalchemy.exc import ProgrammingError

from autotrading.adapters.outbound.sqlalchemy.account_repository import SqlAlchemyAccountRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.tables import accounts
from autotrading.adapters.outbound.sqlalchemy.tenant_repository import SqlAlchemyTenantRepositoryAdapter
from autotrading.application.accounts.errors import AccountNameInUseError
from autotrading.application.tenancy.errors import CrossTenantAccessError
from autotrading.domain.accounts.account import Account
from autotrading.domain.accounts.account_id import AccountId
from autotrading.domain.accounts.account_name import AccountName
from autotrading.domain.accounts.exchange_name import ExchangeName
from autotrading.domain.accounts.sealed_credentials import SealedCredentials
from autotrading.domain.tenancy.tenant import Tenant
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId

pytestmark = pytest.mark.integration


def new_tenant(database: Engine) -> TenantId:
    tenant = Tenant.found_for(UserId(f"oid-{uuid4()}"))
    SqlAlchemyTenantRepositoryAdapter(database).add(tenant)
    return tenant.id


def account_of(tenant_id: TenantId, name: str = "test-1") -> Account:
    sealed = SealedCredentials(key_version=1, ciphertext=b"\x00sealed\xff")
    return Account(AccountId.new(), tenant_id, AccountName(name), ExchangeName("Hyperliquid"), sealed)


def rows_seen(database: Engine, tenant_id: TenantId | None) -> int:
    # A query written without any tenant filter: only row level security stands between tenants.
    with database.begin() as connection:
        if tenant_id is not None:
            connection.execute(select(func.set_config("app.tenant_id", str(tenant_id.value), True)))
        return connection.execute(select(func.count()).select_from(accounts)).scalar_one()


def test_an_added_name_is_in_use_in_its_tenant(database: Engine) -> None:
    tenant = new_tenant(database)
    repository = SqlAlchemyAccountRepositoryAdapter(database, tenant)

    repository.add(account_of(tenant))

    assert repository.name_in_use(AccountName("test-1"))
    assert not repository.name_in_use(AccountName("test-2"))


def test_the_same_name_is_free_in_another_tenant(database: Engine) -> None:
    anna, bruno = new_tenant(database), new_tenant(database)
    SqlAlchemyAccountRepositoryAdapter(database, anna).add(account_of(anna))

    bruno_accounts = SqlAlchemyAccountRepositoryAdapter(database, bruno)

    assert not bruno_accounts.name_in_use(AccountName("test-1"))
    bruno_accounts.add(account_of(bruno))


def test_a_second_account_with_the_same_name_in_the_tenant_is_refused(database: Engine) -> None:
    tenant = new_tenant(database)
    repository = SqlAlchemyAccountRepositoryAdapter(database, tenant)
    repository.add(account_of(tenant))

    with pytest.raises(AccountNameInUseError):
        repository.add(account_of(tenant))


def test_an_account_of_another_tenant_is_refused_before_reaching_the_database(database: Engine) -> None:
    repository = SqlAlchemyAccountRepositoryAdapter(database, new_tenant(database))

    with pytest.raises(CrossTenantAccessError):
        repository.add(account_of(new_tenant(database)))


def test_a_transaction_of_tenant_b_sees_no_row_of_tenant_a(database: Engine) -> None:
    anna, bruno = new_tenant(database), new_tenant(database)
    SqlAlchemyAccountRepositoryAdapter(database, anna).add(account_of(anna, "solo-anna"))

    assert (rows_seen(database, anna), rows_seen(database, bruno)) == (1, 0)


def test_a_transaction_without_a_tenant_sees_no_row(database: Engine) -> None:
    anna = new_tenant(database)
    SqlAlchemyAccountRepositoryAdapter(database, anna).add(account_of(anna))

    assert rows_seen(database, None) == 0


def test_a_row_for_another_tenant_cannot_be_written(database: Engine) -> None:
    anna, bruno = new_tenant(database), new_tenant(database)
    statement = text(
        "INSERT INTO accounts (id, tenant_id, name, exchange, credentials_key_version, credentials_ciphertext) "
        "VALUES (:id, :tenant, 'intruso', 'Hyperliquid', 1, '\\x00')"
    )

    with database.begin() as connection:
        connection.execute(select(func.set_config("app.tenant_id", str(bruno.value), True)))
        with pytest.raises(ProgrammingError, match="row-level security"):
            connection.execute(statement, {"id": uuid4(), "tenant": anna.value})


def test_the_tenant_does_not_survive_the_transaction_on_a_pooled_connection(database: Engine) -> None:
    anna = new_tenant(database)
    SqlAlchemyAccountRepositoryAdapter(database, anna).add(account_of(anna))

    with database.connect() as connection:
        setting = connection.execute(text("SELECT current_setting('app.tenant_id', true)")).scalar_one()

    assert setting in (None, "")
