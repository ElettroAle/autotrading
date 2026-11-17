"""The password of the mail server of a tenant: sealed by the API with the public key, opened only by the worker, and
refused when copied onto another tenant (ADR server-di-posta-per-tenant)."""

import json
import logging

import pytest
from nacl.public import PrivateKey, SealedBox

from autotrading.adapters.outbound.libsodium.mail_password_opener import SodiumMailPasswordOpenerAdapter
from autotrading.adapters.outbound.libsodium.mail_password_sealer import SodiumMailPasswordSealerAdapter
from autotrading.application.notifications.errors import MailPasswordNotOpenedError
from autotrading.domain.notifications.sealed_mail_password import SealedMailPassword
from autotrading.domain.tenancy.tenant_id import TenantId

PASSWORD = "password-per-le-app"  # noqa: S105 - the password of a fake mail server
TENANT = TenantId.new()


@pytest.fixture
def private_key() -> PrivateKey:
    return PrivateKey.generate()


def sealed(private_key: PrivateKey, tenant_id: TenantId = TENANT, version: int = 1) -> SealedMailPassword:
    return SodiumMailPasswordSealerAdapter(bytes(private_key.public_key), version, tenant_id).seal(PASSWORD)


def opener(private_key: PrivateKey, tenant_id: TenantId = TENANT) -> SodiumMailPasswordOpenerAdapter:
    return SodiumMailPasswordOpenerAdapter({1: bytes(private_key)}, tenant_id)


def with_plaintext(private_key: PrivateKey, document: object) -> SealedMailPassword:
    return SealedMailPassword(1, SealedBox(private_key.public_key).encrypt(json.dumps(document).encode()))


def test_opens_what_the_sealer_sealed_for_the_same_tenant(private_key: PrivateKey) -> None:
    assert opener(private_key).open(sealed(private_key)) == PASSWORD


def test_the_sealed_password_carries_the_version_and_hides_the_password(private_key: PrivateKey) -> None:
    password = sealed(private_key, version=3)

    assert password.key_version == 3
    assert PASSWORD.encode() not in password.ciphertext
    assert PASSWORD not in repr(password)


def test_the_sealer_and_the_opener_never_show_their_keys(private_key: PrivateKey) -> None:
    sealer = SodiumMailPasswordSealerAdapter(bytes(private_key.public_key), 4, TENANT)

    assert repr(sealer) == "SodiumMailPasswordSealerAdapter(key_version=4)"
    assert repr(opener(private_key)) == f"SodiumMailPasswordOpenerAdapter(tenant_id={TENANT.value}, key_versions=[1])"


def test_a_password_sealed_for_another_tenant_is_refused(private_key: PrivateKey) -> None:
    copied = sealed(private_key, tenant_id=TenantId.new())

    with pytest.raises(MailPasswordNotOpenedError):
        opener(private_key).open(copied)


def test_a_version_without_its_private_key_is_refused(private_key: PrivateKey) -> None:
    with pytest.raises(MailPasswordNotOpenedError):
        opener(private_key).open(sealed(private_key, version=2))


def test_a_text_sealed_with_another_key_is_refused(private_key: PrivateKey) -> None:
    with pytest.raises(MailPasswordNotOpenedError) as raised:
        opener(private_key).open(sealed(PrivateKey.generate()))

    assert raised.value.__cause__ is not None


@pytest.mark.parametrize(
    "document",
    [
        ["not", "a", "mapping"],
        {"tenant_id": str(TENANT.value)},
        {"tenant_id": str(TENANT.value), "mail_password": 7},
        {"tenant_id": str(TENANT.value), "mail_password": ""},
        {"tenant_id": str(TENANT.value), "provider": "openrouter", "fields": {"api_key": "k"}},
    ],
    ids=["not-a-mapping", "no-password", "not-a-text", "empty", "a-provider-key"],
)
def test_a_text_that_holds_no_password_is_refused(private_key: PrivateKey, document: object) -> None:
    with pytest.raises(MailPasswordNotOpenedError):
        opener(private_key).open(with_plaintext(private_key, document))


def test_a_text_that_is_no_document_is_refused(private_key: PrivateKey) -> None:
    garbage = SealedMailPassword(1, SealedBox(private_key.public_key).encrypt(b"not json"))

    with pytest.raises(MailPasswordNotOpenedError):
        opener(private_key).open(garbage)


def test_every_opening_is_recorded_without_the_password(
    private_key: PrivateKey, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO, logger="autotrading.credentials"):
        opener(private_key).open(sealed(private_key))
        with pytest.raises(MailPasswordNotOpenedError):
            opener(private_key).open(sealed(private_key, tenant_id=TenantId.new()))

    messages = [record.getMessage() for record in caplog.records]
    assert messages == [
        f"decifratura riuscita per posta: tenant {TENANT.value}, server di posta, versione 1",
        f"decifratura rifiutata per posta: tenant {TENANT.value}, server di posta, versione 1",
    ]
    assert all(PASSWORD not in message for message in messages)
