from datetime import UTC, date, datetime
from uuid import uuid4

import pytest
from sqlalchemy import Engine

from autotrading.adapters.outbound.sqlalchemy.source_credentials_repository import (
    SqlAlchemySourceCredentialsRepositoryAdapter,
)
from autotrading.adapters.outbound.sqlalchemy.tenant_repository import SqlAlchemyTenantRepositoryAdapter
from autotrading.application.sources.errors import SourceCredentialsNotFoundError
from autotrading.application.tenancy.errors import CrossTenantAccessError
from autotrading.domain.sources.key_expiry import KeyExpiry
from autotrading.domain.sources.sealed_source_secrets import SealedSourceSecrets
from autotrading.domain.sources.source_credentials import SourceCredentials
from autotrading.domain.tenancy.tenant import Tenant
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId

pytestmark = pytest.mark.integration

PAID = "LunarCrush"
REJECTED_AT = datetime(2026, 11, 15, 10, 0, tzinfo=UTC)


def new_tenant(database: Engine) -> TenantId:
    tenant = Tenant.found_for(UserId(f"oid-{uuid4()}"))
    SqlAlchemyTenantRepositoryAdapter(database).add(tenant)
    return tenant.id


def credentials_of(tenant_id: TenantId, ciphertext: bytes = b"\x00sealed\xff") -> SourceCredentials:
    return SourceCredentials(tenant_id, PAID, {"account": "anna"}, SealedSourceSecrets(1, ciphertext))


def test_saved_credentials_read_back_as_they_were_sealed(database: Engine) -> None:
    anna = new_tenant(database)
    repository = SqlAlchemySourceCredentialsRepositoryAdapter(database, anna)

    repository.save(credentials_of(anna))

    assert repository.get(PAID) == credentials_of(anna)
    [registration] = repository.registrations()
    assert registration.credentials == credentials_of(anna)
    assert registration.registered_at.tzinfo is not None
    assert repository.configured_adapters() == frozenset({PAID})
    assert repository.get("Arkham") is None


def test_a_replacement_takes_the_place_of_the_saved_credentials_and_forgets_the_refusal(database: Engine) -> None:
    anna = new_tenant(database)
    repository = SqlAlchemySourceCredentialsRepositoryAdapter(database, anna)
    repository.save(credentials_of(anna))
    assert repository.mark_rejected(PAID, REJECTED_AT)
    [before] = repository.registrations()

    repository.save(credentials_of(anna, b"new"))

    [after] = repository.registrations()
    assert after.credentials == credentials_of(anna, b"new")
    assert after.registered_at >= before.registered_at


def test_the_refusal_is_kept_once_until_the_credentials_are_replaced(database: Engine) -> None:
    anna = new_tenant(database)
    repository = SqlAlchemySourceCredentialsRepositoryAdapter(database, anna)
    repository.save(credentials_of(anna))

    first, second = repository.mark_rejected(PAID, REJECTED_AT), repository.mark_rejected(PAID, REJECTED_AT)

    assert (first, second) == (True, False)
    stored = repository.get(PAID)
    assert stored is not None
    assert stored.rejected_at == REJECTED_AT
    assert not repository.mark_rejected("Arkham", REJECTED_AT)


def test_the_expiry_is_kept_and_forgotten(database: Engine) -> None:
    anna = new_tenant(database)
    repository = SqlAlchemySourceCredentialsRepositoryAdapter(database, anna)
    repository.save(credentials_of(anna))

    repository.set_expiry(PAID, KeyExpiry.entered(date(2026, 12, 15)))
    dated = repository.get(PAID)
    repository.set_expiry(PAID, None)

    assert dated is not None
    assert dated.expiry == KeyExpiry.entered(date(2026, 12, 15))
    assert repository.get(PAID) == credentials_of(anna)
    with pytest.raises(SourceCredentialsNotFoundError):
        repository.set_expiry("Arkham", None)


def test_removed_credentials_are_gone(database: Engine) -> None:
    anna = new_tenant(database)
    repository = SqlAlchemySourceCredentialsRepositoryAdapter(database, anna)
    repository.save(credentials_of(anna))

    repository.remove(PAID)

    assert repository.registrations() == ()
    with pytest.raises(SourceCredentialsNotFoundError):
        repository.remove(PAID)


def test_a_tenant_never_sees_nor_touches_the_credentials_of_another(database: Engine) -> None:
    anna, bruno = new_tenant(database), new_tenant(database)
    SqlAlchemySourceCredentialsRepositoryAdapter(database, anna).save(credentials_of(anna))
    bruno_credentials = SqlAlchemySourceCredentialsRepositoryAdapter(database, bruno)

    assert bruno_credentials.registrations() == ()
    assert bruno_credentials.configured_adapters() == frozenset()
    assert not bruno_credentials.mark_rejected(PAID, REJECTED_AT)
    with pytest.raises(SourceCredentialsNotFoundError):
        bruno_credentials.remove(PAID)
    with pytest.raises(CrossTenantAccessError):
        bruno_credentials.save(credentials_of(anna, b"stolen"))
    assert SqlAlchemySourceCredentialsRepositoryAdapter(database, anna).get(PAID) == credentials_of(anna)
