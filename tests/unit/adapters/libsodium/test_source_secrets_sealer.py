"""The secret values of the credentials of an adapter of a source, sealed by the API with the public key: it can
encrypt but never decrypt (R4.1.2, ADR credenziali-degli-adapter-delle-fonti)."""

import json

import pytest
from nacl.public import PrivateKey, SealedBox

from autotrading.adapters.outbound.libsodium.sealer import InvalidCredentialsKeyError
from autotrading.adapters.outbound.libsodium.source_secrets_sealer import SodiumSourceSecretsSealerAdapter
from autotrading.domain.tenancy.tenant_id import TenantId

SECRETS = {"api_key": "LC-SEGRETA"}
ADAPTER = "LunarCrush"


@pytest.fixture
def private_key() -> PrivateKey:
    return PrivateKey.generate()


def test_only_the_private_key_opens_what_was_sealed_with_tenant_and_adapter(private_key: PrivateKey) -> None:
    tenant_id = TenantId.new()
    sealer = SodiumSourceSecretsSealerAdapter(bytes(private_key.public_key), 3, tenant_id)

    sealed = sealer.seal(ADAPTER, SECRETS)

    assert sealed.key_version == 3
    assert json.loads(SealedBox(private_key).decrypt(sealed.ciphertext)) == {
        "tenant_id": str(tenant_id.value),
        "adapter": ADAPTER,
        "secrets": SECRETS,
    }


def test_the_sealed_text_never_holds_the_secrets_and_changes_at_every_seal(private_key: PrivateKey) -> None:
    sealer = SodiumSourceSecretsSealerAdapter(bytes(private_key.public_key), 1, TenantId.new())

    first, second = sealer.seal(ADAPTER, SECRETS), sealer.seal(ADAPTER, SECRETS)

    assert b"LC-SEGRETA" not in first.ciphertext
    assert "LC-SEGRETA" not in repr(first)
    assert first.ciphertext != second.ciphertext


def test_the_sealer_never_shows_its_key(private_key: PrivateKey) -> None:
    sealer = SodiumSourceSecretsSealerAdapter(bytes(private_key.public_key), 4, TenantId.new())

    assert repr(sealer) == "SodiumSourceSecretsSealerAdapter(key_version=4)"


def test_a_malformed_public_key_is_refused() -> None:
    with pytest.raises(InvalidCredentialsKeyError):
        SodiumSourceSecretsSealerAdapter(b"short", 1, TenantId.new())
