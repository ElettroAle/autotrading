from uuid import uuid4

import pytest
from sqlalchemy import Engine

from autotrading.adapters.outbound.sqlalchemy.provider_key_repository import SqlAlchemyProviderKeyRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.tenant_repository import SqlAlchemyTenantRepositoryAdapter
from autotrading.application.agent.errors import ProviderKeyAlreadyRegisteredError, ProviderKeyNotFoundError
from autotrading.application.tenancy.errors import CrossTenantAccessError
from autotrading.domain.agent.provider_name import ProviderName
from autotrading.domain.agent.registered_provider_key import RegisteredProviderKey
from autotrading.domain.agent.sealed_provider_key import SealedProviderKey
from autotrading.domain.tenancy.tenant import Tenant
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId

pytestmark = pytest.mark.integration

OPENROUTER, ANTHROPIC = ProviderName("openrouter"), ProviderName("anthropic")


def new_tenant(database: Engine) -> TenantId:
    tenant = Tenant.found_for(UserId(f"oid-{uuid4()}"))
    SqlAlchemyTenantRepositoryAdapter(database).add(tenant)
    return tenant.id


def a_key(tenant_id: TenantId, provider: ProviderName, ciphertext: bytes = b"\x00sealed\xff") -> RegisteredProviderKey:
    return RegisteredProviderKey(tenant_id, provider, SealedProviderKey(1, ciphertext))


def test_a_saved_key_reads_back_as_it_was_sealed(database: Engine) -> None:
    anna = new_tenant(database)
    keys = SqlAlchemyProviderKeyRepositoryAdapter(database, anna)
    keys.add(a_key(anna, OPENROUTER))
    keys.add(a_key(anna, ANTHROPIC, b"other"))

    assert keys.get(OPENROUTER) == a_key(anna, OPENROUTER)
    assert keys.list() == [a_key(anna, ANTHROPIC, b"other"), a_key(anna, OPENROUTER)]
    assert keys.get(ProviderName("openai")) is None


def test_a_tenant_never_sees_nor_touches_the_keys_of_another(database: Engine) -> None:
    anna, bruno = new_tenant(database), new_tenant(database)
    SqlAlchemyProviderKeyRepositoryAdapter(database, anna).add(a_key(anna, OPENROUTER))
    bruno_keys = SqlAlchemyProviderKeyRepositoryAdapter(database, bruno)

    assert bruno_keys.list() == []
    assert bruno_keys.get(OPENROUTER) is None
    with pytest.raises(ProviderKeyNotFoundError):
        bruno_keys.replace(a_key(bruno, OPENROUTER, b"stolen"))
    with pytest.raises(ProviderKeyNotFoundError):
        bruno_keys.remove(OPENROUTER)
    with pytest.raises(CrossTenantAccessError):
        bruno_keys.add(a_key(anna, ANTHROPIC))
    assert SqlAlchemyProviderKeyRepositoryAdapter(database, anna).get(OPENROUTER) == a_key(anna, OPENROUTER)


def test_two_tenants_each_have_their_key_for_the_same_provider(database: Engine) -> None:
    anna, bruno = new_tenant(database), new_tenant(database)
    SqlAlchemyProviderKeyRepositoryAdapter(database, anna).add(a_key(anna, OPENROUTER, b"anna"))
    SqlAlchemyProviderKeyRepositoryAdapter(database, bruno).add(a_key(bruno, OPENROUTER, b"bruno"))

    assert SqlAlchemyProviderKeyRepositoryAdapter(database, bruno).list() == [a_key(bruno, OPENROUTER, b"bruno")]


def test_a_second_key_for_the_same_provider_is_refused(database: Engine) -> None:
    anna = new_tenant(database)
    keys = SqlAlchemyProviderKeyRepositoryAdapter(database, anna)
    keys.add(a_key(anna, OPENROUTER))

    with pytest.raises(ProviderKeyAlreadyRegisteredError):
        keys.add(a_key(anna, OPENROUTER, b"second"))


def test_the_replacement_and_the_removal_change_the_key_of_the_tenant(database: Engine) -> None:
    anna = new_tenant(database)
    keys = SqlAlchemyProviderKeyRepositoryAdapter(database, anna)
    keys.add(a_key(anna, OPENROUTER))

    keys.replace(RegisteredProviderKey(anna, OPENROUTER, SealedProviderKey(2, b"new")))
    assert keys.get(OPENROUTER) == RegisteredProviderKey(anna, OPENROUTER, SealedProviderKey(2, b"new"))

    keys.remove(OPENROUTER)
    assert keys.list() == []
    with pytest.raises(ProviderKeyNotFoundError):
        keys.remove(OPENROUTER)
