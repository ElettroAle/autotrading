import pytest
from sqlalchemy import create_engine

from autotrading.adapters.outbound.sqlalchemy.account_repository import SqlAlchemyAccountRepositoryAdapter, _row_of
from autotrading.application.tenancy.errors import CrossTenantAccessError
from autotrading.domain.accounts.account import Account
from autotrading.domain.accounts.account_id import AccountId
from autotrading.domain.accounts.account_name import AccountName
from autotrading.domain.accounts.exchange_name import ExchangeName
from autotrading.domain.accounts.sealed_credentials import SealedCredentials
from autotrading.domain.tenancy.tenant_id import TenantId

# The engine never connects: these tests stop before the database.
ENGINE = create_engine("postgresql+psycopg://nobody@unreachable.invalid/none")


def account_of(tenant_id: TenantId) -> Account:
    return Account(
        AccountId.new(),
        tenant_id,
        AccountName("test-1"),
        ExchangeName("Hyperliquid"),
        SealedCredentials(3, b"\x01\x02"),
    )


def test_a_row_carries_tenant_name_exchange_and_the_sealed_credentials() -> None:
    account = account_of(TenantId.new())

    assert _row_of(account) == {
        "id": account.id.value,
        "tenant_id": account.tenant_id.value,
        "name": "test-1",
        "exchange": "Hyperliquid",
        "credentials_key_version": 3,
        "credentials_ciphertext": b"\x01\x02",
    }


def test_an_account_of_another_tenant_never_reaches_the_database() -> None:
    repository = SqlAlchemyAccountRepositoryAdapter(ENGINE, TenantId.new())

    with pytest.raises(CrossTenantAccessError) as raised:
        repository.add(account_of(TenantId.new()))

    assert str(raised.value) == "non trovato"
