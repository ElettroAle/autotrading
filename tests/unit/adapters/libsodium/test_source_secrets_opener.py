"""The secret values of the credentials of an adapter of a source, opened only by the worker and refused when copied
onto another tenant or adapter (R4.1.2, ADR credenziali-degli-adapter-delle-fonti).
"""

import json
import logging

import pytest
from nacl.public import PrivateKey, SealedBox

from autotrading.adapters.outbound.libsodium.source_secrets_opener import SodiumSourceSecretsOpenerAdapter
from autotrading.adapters.outbound.libsodium.source_secrets_sealer import SodiumSourceSecretsSealerAdapter
from autotrading.application.sources.errors import SourceSecretsNotOpenedError
from autotrading.domain.sources.sealed_source_secrets import SealedSourceSecrets
from autotrading.domain.sources.source_credentials import SourceCredentials
from autotrading.domain.tenancy.tenant_id import TenantId

SECRETS = {"api_key": "LC-SEGRETA"}
ADAPTER = "LunarCrush"
TENANT = TenantId.new()


@pytest.fixture
def private_key() -> PrivateKey:
    return PrivateKey.generate()


def credentials(
    private_key: PrivateKey, tenant_id: TenantId = TENANT, adapter: str = ADAPTER, version: int = 1
) -> SourceCredentials:
    sealed = SodiumSourceSecretsSealerAdapter(bytes(private_key.public_key), version, tenant_id).seal(adapter, SECRETS)
    return SourceCredentials(TENANT, ADAPTER, {"account": "anna"}, sealed)


def with_plaintext(private_key: PrivateKey, document: object) -> SourceCredentials:
    ciphertext = SealedBox(private_key.public_key).encrypt(json.dumps(document).encode())
    return SourceCredentials(TENANT, ADAPTER, {}, SealedSourceSecrets(1, ciphertext))


def opener(private_key: PrivateKey) -> SodiumSourceSecretsOpenerAdapter:
    return SodiumSourceSecretsOpenerAdapter({1: bytes(private_key)})


def test_opens_what_the_sealer_sealed_for_the_same_tenant_and_adapter(private_key: PrivateKey) -> None:
    assert opener(private_key).open(credentials(private_key)) == SECRETS


def test_the_opener_never_shows_its_keys(private_key: PrivateKey) -> None:
    assert repr(opener(private_key)) == "SodiumSourceSecretsOpenerAdapter(key_versions=[1])"


@pytest.mark.parametrize(
    ("tenant_id", "adapter"), [(TenantId.new(), ADAPTER), (TENANT, "Arkham")], ids=["other-tenant", "other-adapter"]
)
def test_secrets_sealed_for_another_tenant_or_adapter_are_refused(
    private_key: PrivateKey, tenant_id: TenantId, adapter: str
) -> None:
    with pytest.raises(SourceSecretsNotOpenedError):
        opener(private_key).open(credentials(private_key, tenant_id, adapter))


def test_a_version_without_its_private_key_is_refused(private_key: PrivateKey) -> None:
    with pytest.raises(SourceSecretsNotOpenedError):
        opener(private_key).open(credentials(private_key, version=2))


def test_a_text_sealed_with_another_key_is_refused_keeping_the_cause(private_key: PrivateKey) -> None:
    with pytest.raises(SourceSecretsNotOpenedError) as raised:
        opener(private_key).open(credentials(PrivateKey.generate()))

    assert raised.value.__cause__ is not None


@pytest.mark.parametrize(
    "document",
    [
        ["not", "a", "mapping"],
        {"tenant_id": str(TENANT.value), "adapter": ADAPTER},
        {"tenant_id": str(TENANT.value), "adapter": ADAPTER, "secrets": {"api_key": 7}},
        {"tenant_id": str(TENANT.value), "adapter": ADAPTER, "secrets": ["api_key"]},
    ],
    ids=["not-a-mapping", "no-secrets", "not-a-text", "not-fields"],
)
def test_a_text_that_holds_no_secrets_is_refused(private_key: PrivateKey, document: object) -> None:
    with pytest.raises(SourceSecretsNotOpenedError):
        opener(private_key).open(with_plaintext(private_key, document))


def test_a_text_that_is_no_document_is_refused(private_key: PrivateKey) -> None:
    sealed = SealedSourceSecrets(1, SealedBox(private_key.public_key).encrypt(b"x"))
    garbage = SourceCredentials(TENANT, ADAPTER, {}, sealed)

    with pytest.raises(SourceSecretsNotOpenedError):
        opener(private_key).open(garbage)


def test_every_opening_is_recorded_without_the_secrets(
    private_key: PrivateKey, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO, logger="autotrading.credentials"):
        opener(private_key).open(credentials(private_key))
        with pytest.raises(SourceSecretsNotOpenedError):
            opener(private_key).open(credentials(private_key, adapter="Arkham"))

    messages = [record.getMessage() for record in caplog.records]
    assert messages == [
        f"decifratura riuscita per fonte: tenant {TENANT.value}, adapter LunarCrush, versione 1",
        f"decifratura rifiutata per fonte: tenant {TENANT.value}, adapter LunarCrush, versione 1",
    ]
    assert all("LC-SEGRETA" not in message for message in messages)
