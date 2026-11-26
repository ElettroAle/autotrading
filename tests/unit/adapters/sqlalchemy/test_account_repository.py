from dataclasses import replace
from decimal import Decimal

import pytest
from sqlalchemy import create_engine

from autotrading.adapters.outbound.sqlalchemy.account_repository import (
    SqlAlchemyAccountRepositoryAdapter,
    _account_of,
    _row_of,
)
from autotrading.application.tenancy.errors import CrossTenantAccessError
from autotrading.domain.accounts.account import Account
from autotrading.domain.accounts.deviation_threshold import DeviationThreshold
from autotrading.domain.accounts.exchange_account import ExchangeAccount
from autotrading.domain.accounts.sealed_credentials import SealedCredentials
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.support.accounts import ADDRESS, an_account

# The engine never connects: these tests stop before the database.
ENGINE = create_engine("postgresql+psycopg://nobody@unreachable.invalid/none")


def account_of(tenant_id: TenantId) -> Account:
    return an_account(tenant_id, sealed=SealedCredentials(3, b"\x01\x02"))


def test_a_row_carries_tenant_name_exchange_account_and_the_sealed_credentials() -> None:
    account = account_of(TenantId.new())

    assert _row_of(account) == {
        "id": account.id.value,
        "tenant_id": account.tenant_id.value,
        "name": "test-1",
        "exchange": "Hyperliquid",
        "exchange_account_fingerprint": account.exchange_account.fingerprint,
        "exchange_account_public_fields": {"account_address": ADDRESS},
        "credentials_key_version": 3,
        "credentials_ciphertext": b"\x01\x02",
        "deviation_threshold": Decimal(1),
        "expires_on": None,
        "expiry_source": None,
        "max_direction_exposure_percent": None,
    }


def test_a_row_read_back_is_the_same_account() -> None:
    account = account_of(TenantId.new())

    read = _account_of(_row_of(account))  # type: ignore[arg-type]  # a dict stands for the row mapping of a query

    assert read == account
    assert read.exchange_account.public_fields == {"account_address": ADDRESS}


def test_an_account_saved_before_the_public_fields_were_kept_reads_without_them() -> None:
    account = account_of(TenantId.new())
    legacy = replace(account, exchange_account=ExchangeAccount(account.exchange_account.fingerprint))

    row = _row_of(legacy)
    read = _account_of(row)  # type: ignore[arg-type]  # a dict stands for the row mapping of a query

    assert row["exchange_account_public_fields"] is None
    assert read.exchange_account.public_fields is None


@pytest.mark.parametrize("operation", ["add", "replace"])
def test_an_account_of_another_tenant_never_reaches_the_database(operation: str) -> None:
    repository = SqlAlchemyAccountRepositoryAdapter(ENGINE, TenantId.new())

    with pytest.raises(CrossTenantAccessError) as raised:
        getattr(repository, operation)(account_of(TenantId.new()))

    assert str(raised.value) == "non trovato"


def test_the_threshold_of_the_account_is_read_back_as_saved() -> None:
    account = account_of(TenantId.new()).with_deviation_threshold(DeviationThreshold(Decimal("2.5")))

    read = _account_of(_row_of(account))  # type: ignore[arg-type]  # a dict stands for the row mapping of a query

    assert read.deviation_threshold == DeviationThreshold(Decimal("2.5"))


def test_the_max_direction_exposure_of_the_account_is_read_back_as_saved() -> None:
    account = account_of(TenantId.new()).with_max_direction_exposure(Decimal(60))

    read = _account_of(_row_of(account))  # type: ignore[arg-type]  # a dict stands for the row mapping of a query

    assert read.max_direction_exposure_percent == Decimal(60)
