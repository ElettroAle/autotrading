from uuid import uuid4

import pytest
from sqlalchemy import Engine, func, select, text
from sqlalchemy.exc import ProgrammingError

from autotrading.adapters.outbound.sqlalchemy.account_repository import SqlAlchemyAccountRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.tables import accounts
from autotrading.adapters.outbound.sqlalchemy.tenant_repository import SqlAlchemyTenantRepositoryAdapter
from autotrading.application.accounts.errors import AccountNameInUseError
from autotrading.application.flows.errors import FlowAccountNotFoundError
from autotrading.application.orders.errors import OrderAccountNotFoundError
from autotrading.application.tenancy.errors import CrossTenantAccessError
from autotrading.application.verification.errors import VerificationAccountNotFoundError
from autotrading.domain.accounts.account import Account
from autotrading.domain.accounts.account_id import AccountId
from autotrading.domain.accounts.account_name import AccountName
from autotrading.domain.accounts.sealed_credentials import SealedCredentials
from autotrading.domain.flows.sealed_address import SealedAddress
from autotrading.domain.orders.sealed_access import SealedAccess
from autotrading.domain.tenancy.tenant import Tenant
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId
from autotrading.domain.verification.verification_access import SealedVerificationAccess
from tests.support.accounts import an_account

pytestmark = pytest.mark.integration


def new_tenant(database: Engine) -> TenantId:
    tenant = Tenant.found_for(UserId(f"oid-{uuid4()}"))
    SqlAlchemyTenantRepositoryAdapter(database).add(tenant)
    return tenant.id


def account_of(tenant_id: TenantId, name: str = "test-1") -> Account:
    return an_account(tenant_id, name, SealedCredentials(key_version=1, ciphertext=b"\x00sealed\xff"))


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
        "INSERT INTO accounts (id, tenant_id, name, exchange, exchange_account_fingerprint, "
        "credentials_key_version, credentials_ciphertext) "
        "VALUES (:id, :tenant, 'intruso', 'Hyperliquid', 'f', 1, '\\x00')"
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


def test_the_tenant_lists_its_accounts_by_name_and_only_those(database: Engine) -> None:
    anna, bruno = new_tenant(database), new_tenant(database)
    repository = SqlAlchemyAccountRepositoryAdapter(database, anna)
    second, first = account_of(anna, "test-2"), account_of(anna, "test-1")
    repository.add(second)
    repository.add(first)
    SqlAlchemyAccountRepositoryAdapter(database, bruno).add(account_of(bruno, "conto-bruno"))

    assert repository.list() == [first, second]


def test_an_account_read_back_is_the_one_saved(database: Engine) -> None:
    anna = new_tenant(database)
    repository = SqlAlchemyAccountRepositoryAdapter(database, anna)
    account = account_of(anna)
    repository.add(account)

    assert repository.get(account.id) == account


def test_an_account_of_another_tenant_reads_as_missing(database: Engine) -> None:
    anna, bruno = new_tenant(database), new_tenant(database)
    account = account_of(anna)
    SqlAlchemyAccountRepositoryAdapter(database, anna).add(account)

    bruno_accounts = SqlAlchemyAccountRepositoryAdapter(database, bruno)

    assert (bruno_accounts.get(account.id), bruno_accounts.get(AccountId.new())) == (None, None)


def test_a_flow_learns_the_exchange_of_an_account_of_its_tenant_only(database: Engine) -> None:
    anna, bruno = new_tenant(database), new_tenant(database)
    account = account_of(anna)
    SqlAlchemyAccountRepositoryAdapter(database, anna).add(account)

    assert SqlAlchemyAccountRepositoryAdapter(database, anna).exchange_of(account.id.value) == account.exchange.value
    for tenant_id, account_id in ((bruno, account.id), (anna, AccountId.new())):
        with pytest.raises(FlowAccountNotFoundError):
            SqlAlchemyAccountRepositoryAdapter(database, tenant_id).exchange_of(account_id.value)


def test_replaced_credentials_leave_no_trace_of_the_previous_ones(database: Engine) -> None:
    anna = new_tenant(database)
    repository = SqlAlchemyAccountRepositoryAdapter(database, anna)
    account = account_of(anna)
    repository.add(account)
    replaced = account.with_credentials(SealedCredentials(key_version=1, ciphertext=b"new"))

    repository.replace(replaced)

    assert repository.get(account.id) == replaced
    assert ciphertexts(database, anna) == [b"new"]


def test_an_account_hidden_by_row_level_security_is_not_replaced(database: Engine) -> None:
    anna = new_tenant(database)
    account = account_of(anna)
    SqlAlchemyAccountRepositoryAdapter(database, anna).add(account)
    other = new_tenant(database)
    # The same account presented as one of the other tenant: the guard passes, row level security does not.
    disguised = Account(
        account.id, other, account.name, account.exchange, account.exchange_account, account.credentials
    )

    with pytest.raises(CrossTenantAccessError):
        SqlAlchemyAccountRepositoryAdapter(database, other).replace(disguised)


def ciphertexts(database: Engine, tenant_id: TenantId) -> list[bytes]:
    with database.begin() as connection:
        connection.execute(select(func.set_config("app.tenant_id", str(tenant_id.value), True)))
        return list(connection.execute(select(accounts.c.credentials_ciphertext)).scalars())


def test_the_sealed_access_of_an_account_is_read_for_its_tenant_only(database: Engine) -> None:
    tenant_a, tenant_b = new_tenant(database), new_tenant(database)
    account = account_of(tenant_a)
    SqlAlchemyAccountRepositoryAdapter(database, tenant_a).add(account)

    sealed = SqlAlchemyAccountRepositoryAdapter(database, tenant_a).sealed_access(account.id.value)

    assert sealed == SealedAccess(tenant_a, account.id.value, account.exchange.value, 1, b"\x00sealed\xff")
    with pytest.raises(OrderAccountNotFoundError):
        SqlAlchemyAccountRepositoryAdapter(database, tenant_b).sealed_access(account.id.value)


def test_the_sealed_address_of_an_account_is_read_for_its_tenant_only(database: Engine) -> None:
    tenant_a, tenant_b = new_tenant(database), new_tenant(database)
    account = account_of(tenant_a)
    SqlAlchemyAccountRepositoryAdapter(database, tenant_a).add(account)

    sealed = SqlAlchemyAccountRepositoryAdapter(database, tenant_a).sealed_address(account.id.value)

    assert sealed == SealedAddress(tenant_a, account.id.value, account.exchange.value, 1, b"\x00sealed\xff")
    with pytest.raises(FlowAccountNotFoundError):
        SqlAlchemyAccountRepositoryAdapter(database, tenant_b).sealed_address(account.id.value)


def test_the_sealed_verification_access_of_an_account_is_read_for_its_tenant_only(database: Engine) -> None:
    tenant_a, tenant_b = new_tenant(database), new_tenant(database)
    account = account_of(tenant_a)
    SqlAlchemyAccountRepositoryAdapter(database, tenant_a).add(account)

    sealed = SqlAlchemyAccountRepositoryAdapter(database, tenant_a).sealed_verification(account.id.value)

    assert sealed == SealedVerificationAccess(
        tenant_a, account.id.value, account.exchange.value, 1, account.credentials.ciphertext
    )
    with pytest.raises(VerificationAccountNotFoundError):
        SqlAlchemyAccountRepositoryAdapter(database, tenant_b).sealed_verification(account.id.value)
