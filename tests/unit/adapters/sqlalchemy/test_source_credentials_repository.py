"""The rows of the credentials of the adapters of the sources, read and written without a database: the repository
against PostgreSQL is in tests/integration/sqlalchemy/test_source_credentials_repository.py (R4.1.2)."""

from datetime import date

import pytest
from sqlalchemy import create_engine

from autotrading.adapters.outbound.sqlalchemy.source_credentials_repository import (
    SqlAlchemySourceCredentialsRepositoryAdapter,
    _credentials_of,
    _row_of,
)
from autotrading.application.tenancy.errors import CrossTenantAccessError
from autotrading.domain.sources.key_expiry import KeyExpiry
from autotrading.domain.sources.sealed_source_secrets import SealedSourceSecrets
from autotrading.domain.sources.source_credentials import SourceCredentials
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.support.source_keys import REJECTED_AT

# The engine never connects: these tests stop before the database.
ENGINE = create_engine("postgresql+psycopg://nobody@unreachable.invalid/none")
PAID = "LunarCrush"


def credentials_of(tenant_id: TenantId, expiry: KeyExpiry | None = None) -> SourceCredentials:
    return SourceCredentials(tenant_id, PAID, {"account": "anna"}, SealedSourceSecrets(2, b"\x01\x02"), expiry)


def test_a_row_carries_tenant_adapter_public_values_and_the_sealed_secrets() -> None:
    tenant_id = TenantId.new()

    assert _row_of(credentials_of(tenant_id).rejected(REJECTED_AT)) == {
        "tenant_id": tenant_id.value,
        "adapter": PAID,
        "public_values": {"account": "anna"},
        "key_version": 2,
        "ciphertext": b"\x01\x02",
        "rejected_at": REJECTED_AT,
        "expires_on": None,
        "expiry_source": None,
    }


@pytest.mark.parametrize("expiry", [None, KeyExpiry.entered(date(2026, 12, 15))], ids=["no-date", "entered"])
def test_a_row_read_back_is_the_same_credentials(expiry: KeyExpiry | None) -> None:
    saved = credentials_of(TenantId.new(), expiry)

    read = _credentials_of(_row_of(saved))  # type: ignore[arg-type]  # a dict stands for the row mapping of a query

    assert read == saved


def test_public_values_that_are_not_a_mapping_read_as_none() -> None:
    row = {**_row_of(credentials_of(TenantId.new())), "public_values": ["account"]}

    read = _credentials_of(row)  # type: ignore[arg-type]  # a dict stands for the row mapping of a query

    assert dict(read.public_values) == {}


def test_the_credentials_of_another_tenant_are_refused_before_the_database() -> None:
    repository = SqlAlchemySourceCredentialsRepositoryAdapter(ENGINE, TenantId.new())

    with pytest.raises(CrossTenantAccessError):
        repository.save(credentials_of(TenantId.new()))
