from datetime import date

import pytest

from autotrading.application.agent.errors import KeyExpiryReadByAdapterError, ProviderKeyNotFoundError
from autotrading.application.agent.set_provider_key_expiry import (
    SetProviderKeyExpiryCommand,
    SetProviderKeyExpiryUseCase,
)
from autotrading.domain.agent.key_expiry import KeyExpiry
from autotrading.domain.agent.provider_name import ProviderName
from autotrading.domain.agent.registered_provider_key import RegisteredProviderKey
from autotrading.domain.agent.sealed_provider_key import SealedProviderKey
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.model_catalog import InMemoryModelCatalogAdapter
from tests.fakes.provider_keys import InMemoryProviderKeyRepositoryAdapter, ProviderKeyStore
from tests.support.model_catalog import PLATFORM_MODELS

ANNA, BRUNO = TenantId.new(), TenantId.new()
OPENROUTER = ProviderName("openrouter")


@pytest.fixture
def store() -> ProviderKeyStore:
    store = ProviderKeyStore()
    store.keys.append(RegisteredProviderKey(ANNA, OPENROUTER, SealedProviderKey(1, b"sealed")))
    return store


def set_expiry(
    store: ProviderKeyStore, command: SetProviderKeyExpiryCommand, reading: frozenset[str] = frozenset()
) -> None:
    catalogs = {"models": InMemoryModelCatalogAdapter(PLATFORM_MODELS, reading_expiry=reading)}
    SetProviderKeyExpiryUseCase(InMemoryProviderKeyRepositoryAdapter(store, ANNA), catalogs).execute(command)


def test_the_user_gives_the_expiry_of_a_key(store: ProviderKeyStore) -> None:
    set_expiry(store, SetProviderKeyExpiryCommand("openrouter", date(2026, 12, 15)))

    assert store.keys[0].expiry == KeyExpiry.entered(date(2026, 12, 15))


def test_no_date_forgets_the_one_given_before(store: ProviderKeyStore) -> None:
    store.keys[0] = store.keys[0].with_expiry(KeyExpiry.entered(date(2026, 12, 15)))

    set_expiry(store, SetProviderKeyExpiryCommand("openrouter", None))

    assert store.keys[0].expiry is None


def test_the_expiry_a_gateway_reads_cannot_be_given_by_the_user(store: ProviderKeyStore) -> None:
    with pytest.raises(KeyExpiryReadByAdapterError):
        set_expiry(store, SetProviderKeyExpiryCommand("openrouter", date(2026, 12, 15)), frozenset({"openrouter"}))

    assert store.keys[0].expiry is None


def test_a_key_the_tenant_does_not_have_is_not_found(store: ProviderKeyStore) -> None:
    store.keys.append(RegisteredProviderKey(BRUNO, ProviderName("anthropic"), SealedProviderKey(1, b"theirs")))

    with pytest.raises(ProviderKeyNotFoundError):
        set_expiry(store, SetProviderKeyExpiryCommand("anthropic", date(2026, 12, 15)))
