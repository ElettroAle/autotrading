import json

import pytest
from nacl.public import PrivateKey, SealedBox

from autotrading.adapters.outbound.libsodium.sealer import InvalidCredentialsKeyError, SodiumCredentialSealerAdapter
from autotrading.domain.accounts.account_id import AccountId
from autotrading.domain.accounts.credentials import Credentials
from autotrading.domain.tenancy.tenant_id import TenantId

CREDENTIALS = Credentials("0x1111111111111111111111111111111111111111", "0x" + "cd" * 32)


@pytest.fixture
def private_key() -> PrivateKey:
    return PrivateKey.generate()


def test_only_the_private_key_opens_what_was_sealed_with_tenant_and_account(private_key: PrivateKey) -> None:
    tenant_id, account_id = TenantId.new(), AccountId.new()
    sealer = SodiumCredentialSealerAdapter(bytes(private_key.public_key), 2, tenant_id)

    sealed = sealer.seal(account_id, CREDENTIALS)

    assert json.loads(SealedBox(private_key).decrypt(sealed.ciphertext)) == {
        "tenant_id": str(tenant_id.value),
        "account_id": str(account_id.value),
        "account_address": CREDENTIALS.account_address,
        "secret_key": CREDENTIALS.secret_key,
    }


def test_the_sealed_text_carries_the_key_version_and_never_the_secret(private_key: PrivateKey) -> None:
    sealer = SodiumCredentialSealerAdapter(bytes(private_key.public_key), 7, TenantId.new())

    sealed = sealer.seal(AccountId.new(), CREDENTIALS)

    assert sealed.key_version == 7
    assert CREDENTIALS.secret_key.encode() not in sealed.ciphertext


def test_sealing_twice_gives_different_texts(private_key: PrivateKey) -> None:
    sealer = SodiumCredentialSealerAdapter(bytes(private_key.public_key), 1, TenantId.new())
    account_id = AccountId.new()

    first, second = sealer.seal(account_id, CREDENTIALS), sealer.seal(account_id, CREDENTIALS)

    assert first.ciphertext != second.ciphertext


@pytest.mark.parametrize("raw", [b"", b"short", b"x" * 33], ids=["empty", "short", "long"])
def test_refuses_a_public_key_of_the_wrong_size(raw: bytes) -> None:
    with pytest.raises(InvalidCredentialsKeyError) as raised:
        SodiumCredentialSealerAdapter(raw, 1, TenantId.new())

    assert str(raised.value) == "chiave pubblica delle credenziali non valida"


def test_representation_names_only_the_key_version(private_key: PrivateKey) -> None:
    sealer = SodiumCredentialSealerAdapter(bytes(private_key.public_key), 4, TenantId.new())

    assert repr(sealer) == "SodiumCredentialSealerAdapter(key_version=4)"
