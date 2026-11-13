from uuid import uuid4

import pytest
from sqlalchemy import Engine, RowMapping, func, select, text
from sqlalchemy.exc import IntegrityError

from autotrading.adapters.outbound.sqlalchemy.account_repository import SqlAlchemyAccountRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.order_repository import SqlAlchemyOrderRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.tables import accounts, orders
from autotrading.adapters.outbound.sqlalchemy.tenant_repository import SqlAlchemyTenantRepositoryAdapter
from autotrading.application.flows.errors import AccountToRemoveNotFoundError
from autotrading.domain.accounts.account import Account
from autotrading.domain.accounts.account_id import AccountId
from autotrading.domain.accounts.account_name import AccountName
from autotrading.domain.accounts.sealed_credentials import SealedCredentials
from autotrading.domain.tenancy.tenant import Tenant
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId
from tests.support.accounts import an_account
from tests.support.orders import an_executed_order

pytestmark = pytest.mark.integration


def new_tenant(database: Engine) -> TenantId:
    tenant = Tenant.found_for(UserId(f"oid-{uuid4()}"))
    SqlAlchemyTenantRepositoryAdapter(database).add(tenant)
    return tenant.id


def saved_account(database: Engine, tenant_id: TenantId, name: str = "test-1") -> Account:
    account = an_account(tenant_id, name, SealedCredentials(key_version=1, ciphertext=b"\x00sealed\xff"))
    SqlAlchemyAccountRepositoryAdapter(database, tenant_id).add(account)
    return account


def account_rows(database: Engine, tenant_id: TenantId) -> list[RowMapping]:
    # Every row of the tenant, removed or not: what the database keeps.
    with database.begin() as connection:
        connection.execute(select(func.set_config("app.tenant_id", str(tenant_id.value), True)))
        return list(connection.execute(select(accounts)).mappings())


def test_a_removed_account_keeps_its_row_without_credentials(database: Engine) -> None:
    anna = new_tenant(database)
    account = saved_account(database, anna)

    SqlAlchemyAccountRepositoryAdapter(database, anna).remove_account(account.id.value)

    (row,) = account_rows(database, anna)
    assert (row["id"], row["credentials_key_version"], row["credentials_ciphertext"]) == (account.id.value, None, None)
    assert row["removed_at"] is not None


def test_a_removed_account_is_neither_listed_nor_found_nor_replaced(database: Engine) -> None:
    anna = new_tenant(database)
    account = saved_account(database, anna)
    repository = SqlAlchemyAccountRepositoryAdapter(database, anna)

    repository.remove_account(account.id.value)

    assert (repository.list(), repository.get(account.id)) == ([], None)
    assert not repository.name_in_use(AccountName("test-1"))


def test_the_name_of_a_removed_account_can_be_used_again(database: Engine) -> None:
    anna = new_tenant(database)
    removed = saved_account(database, anna)
    SqlAlchemyAccountRepositoryAdapter(database, anna).remove_account(removed.id.value)

    again = saved_account(database, anna)

    assert SqlAlchemyAccountRepositoryAdapter(database, anna).list() == [again]
    assert len(account_rows(database, anna)) == 2


def test_the_orders_of_a_removed_account_stay(database: Engine) -> None:
    anna = new_tenant(database)
    account = saved_account(database, anna)
    order = an_executed_order(account.id.value)
    SqlAlchemyOrderRepositoryAdapter(database, anna).add(order)

    SqlAlchemyAccountRepositoryAdapter(database, anna).remove_account(account.id.value)

    with database.begin() as connection:
        connection.execute(select(func.set_config("app.tenant_id", str(anna.value), True)))
        kept = list(connection.execute(select(orders.c.id, orders.c.account_id)))
    assert [tuple(row) for row in kept] == [(order.id.value, account.id.value)]


@pytest.mark.parametrize("whose", ["missing", "removed", "another-tenant"])
def test_an_account_the_tenant_cannot_remove_is_not_found(database: Engine, whose: str) -> None:
    anna = new_tenant(database)
    repository = SqlAlchemyAccountRepositoryAdapter(database, anna)
    if whose == "missing":
        account_id = AccountId.new()
    elif whose == "removed":
        account_id = saved_account(database, anna).id
        repository.remove_account(account_id.value)
    else:
        account_id = saved_account(database, new_tenant(database)).id

    with pytest.raises(AccountToRemoveNotFoundError):
        repository.remove_account(account_id.value)


@pytest.mark.parametrize(("whose", "held"), [("own", True), ("removed", False), ("another-tenant", False)])
def test_the_removal_sees_only_the_accounts_the_tenant_still_holds(database: Engine, whose: str, held: bool) -> None:
    anna = new_tenant(database)
    repository = SqlAlchemyAccountRepositoryAdapter(database, anna)
    owner = anna if whose != "another-tenant" else new_tenant(database)
    account_id = saved_account(database, owner).id
    if whose == "removed":
        repository.remove_account(account_id.value)

    assert repository.has_account(account_id.value) is held


def test_an_account_in_use_cannot_lose_its_credentials(database: Engine) -> None:
    anna = new_tenant(database)
    account = saved_account(database, anna)

    with database.begin() as connection:
        connection.execute(select(func.set_config("app.tenant_id", str(anna.value), True)))
        with pytest.raises(IntegrityError, match="accounts_credentials_unless_removed"):
            connection.execute(
                text("UPDATE accounts SET credentials_ciphertext = NULL WHERE id = :id"), {"id": account.id.value}
            )
