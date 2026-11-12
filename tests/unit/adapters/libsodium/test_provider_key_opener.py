import json

import pytest
from nacl.public import PrivateKey, SealedBox

from autotrading.adapters.outbound.libsodium.provider_key_opener import SodiumProviderKeyOpenerAdapter
from autotrading.adapters.outbound.libsodium.provider_key_sealer import SodiumProviderKeySealerAdapter
from autotrading.application.agent.errors import ProviderKeyNotOpenedError
from autotrading.domain.agent.provider_key import ProviderKey
from autotrading.domain.agent.provider_name import ProviderName
from autotrading.domain.agent.registered_provider_key import RegisteredProviderKey
from autotrading.domain.agent.sealed_provider_key import SealedProviderKey
from autotrading.domain.tenancy.tenant_id import TenantId

KEY = ProviderKey("K-FAKE-OPENER")
TENANT = TenantId.new()
OPENROUTER = ProviderName("openrouter")


@pytest.fixture
def private_key() -> PrivateKey:
    return PrivateKey.generate()


def registered(
    private_key: PrivateKey, tenant_id: TenantId = TENANT, provider: ProviderName = OPENROUTER, version: int = 1
) -> RegisteredProviderKey:
    sealer = SodiumProviderKeySealerAdapter(bytes(private_key.public_key), version, tenant_id)
    return RegisteredProviderKey(tenant_id, provider, sealer.seal(provider, KEY))


def with_plaintext(private_key: PrivateKey, plaintext: bytes) -> RegisteredProviderKey:
    return RegisteredProviderKey(
        TENANT, OPENROUTER, SealedProviderKey(1, SealedBox(private_key.public_key).encrypt(plaintext))
    )


def test_opens_what_the_sealer_sealed_for_the_same_tenant_and_provider(private_key: PrivateKey) -> None:
    opener = SodiumProviderKeyOpenerAdapter({1: bytes(private_key)})

    assert opener.open(registered(private_key)).secret == KEY.secret


def test_the_private_key_follows_the_version_saved_with_the_sealed_text(private_key: PrivateKey) -> None:
    newer = PrivateKey.generate()
    opener = SodiumProviderKeyOpenerAdapter({1: bytes(private_key), 2: bytes(newer)})

    assert opener.open(registered(newer, version=2)).secret == KEY.secret


def test_a_version_without_its_private_key_is_not_opened(private_key: PrivateKey) -> None:
    opener = SodiumProviderKeyOpenerAdapter({1: bytes(private_key)})

    with pytest.raises(ProviderKeyNotOpenedError, match="chiave del fornitore non leggibile: openrouter"):
        opener.open(registered(private_key, version=2))


def test_a_key_sealed_for_another_tenant_is_refused(private_key: PrivateKey) -> None:
    opener = SodiumProviderKeyOpenerAdapter({1: bytes(private_key)})
    copied = registered(private_key, tenant_id=TenantId.new())

    with pytest.raises(ProviderKeyNotOpenedError):
        opener.open(RegisteredProviderKey(TENANT, OPENROUTER, copied.sealed))


def test_a_key_sealed_for_another_provider_is_refused(private_key: PrivateKey) -> None:
    opener = SodiumProviderKeyOpenerAdapter({1: bytes(private_key)})
    copied = registered(private_key, provider=ProviderName("anthropic"))

    with pytest.raises(ProviderKeyNotOpenedError):
        opener.open(RegisteredProviderKey(TENANT, OPENROUTER, copied.sealed))


def test_a_text_sealed_with_another_key_is_refused(private_key: PrivateKey) -> None:
    opener = SodiumProviderKeyOpenerAdapter({1: bytes(private_key)})

    with pytest.raises(ProviderKeyNotOpenedError):
        opener.open(registered(PrivateKey.generate()))


@pytest.mark.parametrize(
    "plaintext",
    [
        b"not json",
        b"[1, 2]",
        json.dumps({"tenant_id": str(TENANT.value), "provider": "openrouter"}).encode(),
        json.dumps({"tenant_id": str(TENANT.value), "provider": "openrouter", "key": 7}).encode(),
    ],
)
def test_a_document_that_is_not_a_sealed_key_is_refused(private_key: PrivateKey, plaintext: bytes) -> None:
    opener = SodiumProviderKeyOpenerAdapter({1: bytes(private_key)})

    with pytest.raises(ProviderKeyNotOpenedError):
        opener.open(with_plaintext(private_key, plaintext))


def test_the_representation_shows_only_the_key_versions(private_key: PrivateKey) -> None:
    opener = SodiumProviderKeyOpenerAdapter({2: bytes(private_key), 1: bytes(PrivateKey.generate())})

    assert repr(opener) == "SodiumProviderKeyOpenerAdapter(key_versions=[1, 2])"
