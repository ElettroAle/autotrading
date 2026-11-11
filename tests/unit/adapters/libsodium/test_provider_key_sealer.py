import json

import pytest
from nacl.public import PrivateKey, SealedBox

from autotrading.adapters.outbound.libsodium.provider_key_sealer import SodiumProviderKeySealerAdapter
from autotrading.adapters.outbound.libsodium.sealer import InvalidCredentialsKeyError
from autotrading.domain.agent.provider_key import ProviderKey
from autotrading.domain.agent.provider_name import ProviderName
from autotrading.domain.tenancy.tenant_id import TenantId

KEY = ProviderKey("sk-or-v1-0123456789")
OPENROUTER = ProviderName("openrouter")


@pytest.fixture
def private_key() -> PrivateKey:
    return PrivateKey.generate()


def test_only_the_private_key_opens_what_was_sealed_with_tenant_and_provider(private_key: PrivateKey) -> None:
    tenant_id = TenantId.new()
    sealer = SodiumProviderKeySealerAdapter(bytes(private_key.public_key), 3, tenant_id)

    sealed = sealer.seal(OPENROUTER, KEY)

    assert sealed.key_version == 3
    assert json.loads(SealedBox(private_key).decrypt(sealed.ciphertext)) == {
        "tenant_id": str(tenant_id.value),
        "provider": "openrouter",
        "key": KEY.secret,
    }


def test_the_sealed_text_never_holds_the_key_and_changes_at_every_seal(private_key: PrivateKey) -> None:
    sealer = SodiumProviderKeySealerAdapter(bytes(private_key.public_key), 1, TenantId.new())

    first, second = sealer.seal(OPENROUTER, KEY), sealer.seal(OPENROUTER, KEY)

    assert KEY.secret.encode() not in first.ciphertext
    assert first.ciphertext != second.ciphertext


def test_the_sealer_never_shows_its_key(private_key: PrivateKey) -> None:
    public_key = bytes(private_key.public_key)

    assert repr(SodiumProviderKeySealerAdapter(public_key, 4, TenantId.new())) == (
        "SodiumProviderKeySealerAdapter(key_version=4)"
    )


def test_a_malformed_public_key_is_refused() -> None:
    with pytest.raises(InvalidCredentialsKeyError):
        SodiumProviderKeySealerAdapter(b"short", 1, TenantId.new())
