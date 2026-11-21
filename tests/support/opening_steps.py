"""The register of the openings of the credentials of an account and of the keys of the AI providers, read as the
threat model reads it (Bug 179).

The platform seals and opens the credentials with libsodium, as an installation does: the register is written by the
opener of the worker, so a fake opener would leave nothing to read.
"""

import logging
import time
from dataclasses import replace
from uuid import UUID

import pytest
from nacl.public import PrivateKey
from pytest_bdd import given, then

from autotrading.adapters.outbound.libsodium.opener import SodiumCredentialOpenerAdapter, decryptions
from autotrading.adapters.outbound.libsodium.provider_key_opener import SodiumProviderKeyOpenerAdapter
from autotrading.adapters.outbound.libsodium.provider_key_sealer import SodiumProviderKeySealerAdapter
from autotrading.adapters.outbound.libsodium.sealer import SodiumCredentialSealerAdapter
from autotrading.application.accounts.ports import CredentialSealerPort
from autotrading.domain.accounts.credentials import Credentials
from autotrading.domain.agent.provider_name import ProviderName
from autotrading.domain.agent.registered_provider_key import RegisteredProviderKey
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.support.cycle_composition import CycleServices
from tests.support.flow_cycles import FlowCycles
from tests.support.platform import Platform
from tests.support.provider_key import api_key_of
from tests.support.steps import quoted

KEY_VERSION = 1
OUTCOMES = {"riuscita": "decifratura riuscita", "rifiutata": "decifratura rifiutata"}
PROVIDER_KEY = "sk-or-sealed-0123456789"


class SealedPlatform(Platform):
    """The platform with the credentials of the accounts sealed by the API and opened by the worker with libsodium."""

    def __init__(self) -> None:
        super().__init__()
        self.started_at = time.time()
        self.issued: list[Credentials] = []
        self._sealing_key = PrivateKey.generate()
        self._opening_key = self._sealing_key

    def accepted_credentials(self) -> Credentials:
        credentials = super().accepted_credentials()
        self.issued.append(credentials)
        return credentials

    def sealer_of(self, tenant_id: TenantId) -> CredentialSealerPort:
        return SodiumCredentialSealerAdapter(bytes(self._sealing_key.public_key), KEY_VERSION, tenant_id)

    def credential_opener(self) -> SodiumCredentialOpenerAdapter:
        return SodiumCredentialOpenerAdapter({KEY_VERSION: bytes(self._opening_key)})

    def lose_opening_key(self) -> None:
        """The worker holds a private key for the same version that is not the one the API sealed with."""
        self._opening_key = PrivateKey.generate()


@pytest.fixture(autouse=True)
def openings(caplog: pytest.LogCaptureFixture) -> pytest.LogCaptureFixture:
    # import-linter, run by an earlier test, configures logging and disables the loggers that already exist;
    # the platform runs without it, so the register is restored to how it is in an installation.
    decryptions.disabled = False
    caplog.set_level(logging.INFO, logger=decryptions.name)
    return caplog


def openings_of(caplog: pytest.LogCaptureFixture, account_id: UUID) -> list[logging.LogRecord]:
    return [
        record
        for record in caplog.records
        if record.name == decryptions.name and f"conto {account_id}," in record.getMessage()
    ]


def assert_recorded(platform: SealedPlatform, record: logging.LogRecord, tenant_id: TenantId, outcome: str) -> None:
    message = record.getMessage()
    assert message.startswith(OUTCOMES[outcome]), message
    assert f"tenant {tenant_id.value}," in message
    assert message.endswith(f"versione {KEY_VERSION}"), message
    assert platform.started_at <= record.created <= time.time()


@given(quoted('che le credenziali salvate del conto "{account}" non si possono più aprire'))
def credentials_no_longer_open(platform: SealedPlatform, account: str) -> None:
    assert platform.account_named("anna", account)
    platform.lose_opening_key()


@then(
    quoted(
        'l\'apertura delle credenziali del conto "{account}" è registrata con il tenant, la versione della chiave, '
        "l'esito \"{outcome}\" e l'istante"
    )
)
def last_opening_recorded(
    platform: SealedPlatform, openings: pytest.LogCaptureFixture, account: str, outcome: str
) -> None:
    saved = platform.account_named("anna", account)
    recorded = openings_of(openings, saved.id.value)
    assert recorded, "no opening of the credentials was recorded"
    assert_recorded(platform, recorded[-1], saved.tenant_id, outcome)


@then(
    quoted(
        'ogni apertura delle credenziali del conto "{account}" è registrata con il tenant, la versione della chiave, '
        "l'esito \"{outcome}\" e l'istante"
    )
)
def every_opening_recorded(
    platform: SealedPlatform, openings: pytest.LogCaptureFixture, account: str, outcome: str
) -> None:
    saved = platform.account_named("anna", account)
    recorded = openings_of(openings, saved.id.value)
    assert recorded, "no opening of the credentials was recorded"
    for record in recorded:
        assert_recorded(platform, record, saved.tenant_id, outcome)


@then(quoted('la registrazione non contiene le credenziali del conto "{account}"'))
def register_without_credentials(platform: SealedPlatform, openings: pytest.LogCaptureFixture, account: str) -> None:
    recorded = openings_of(openings, platform.account_named("anna", account).id.value)
    assert recorded, "no opening of the credentials was recorded"
    texts = [f"{record.getMessage()} {vars(record)}".lower() for record in recorded]
    secrets = [value.lower() for credentials in platform.issued for value in credentials.values.values()]
    assert secrets, "no credentials were issued"
    assert not [secret for secret in secrets if any(secret in text for text in texts)]


class SealedFlowCycles(FlowCycles):
    """The cycles of the worker with the keys of the AI providers sealed by the API and opened with libsodium
    (Bug 179)."""

    def __init__(self) -> None:
        self._sealing_key = PrivateKey.generate()
        self._opening_key = self._sealing_key
        super().__init__()
        self.started_at = time.time()

    def register_key(self, tenant_id: TenantId, provider: str) -> None:
        name = ProviderName(provider)
        if any(key.provider == name for key in self.platform.provider_keys.of(tenant_id)):
            return
        sealer = SodiumProviderKeySealerAdapter(bytes(self._sealing_key.public_key), KEY_VERSION, tenant_id)
        key = RegisteredProviderKey(tenant_id, name, sealer.seal(name, api_key_of(PROVIDER_KEY)))
        self.platform.provider_keys.keys.append(key)
        self.platform.provider_keys.stamp(key)

    def services(self) -> CycleServices:
        opener = SodiumProviderKeyOpenerAdapter({KEY_VERSION: bytes(self._opening_key)})
        return replace(super().services(), provider_key_opener=opener)

    def lose_opening_key(self) -> None:
        """The worker holds a private key for the same version that is not the one the API sealed with."""
        self._opening_key = PrivateKey.generate()


def key_openings_of(caplog: pytest.LogCaptureFixture, provider: str) -> list[logging.LogRecord]:
    return [
        record
        for record in caplog.records
        if record.name == decryptions.name
        and record.getMessage().endswith(f"chiave {provider}, versione {KEY_VERSION}")
    ]


@given(quoted('che la chiave salvata del fornitore "{provider}" non si può più aprire'))
def provider_key_no_longer_opens(flow_cycles: SealedFlowCycles, provider: str) -> None:
    assert any(key.provider.value == provider for key in flow_cycles.platform.provider_keys.keys)
    flow_cycles.lose_opening_key()


@then(
    quoted(
        'l\'apertura della chiave del fornitore "{provider}" è registrata con il tenant, la versione della chiave, '
        "l'esito \"{outcome}\" e l'istante"
    )
)
def key_opening_recorded(
    flow_cycles: SealedFlowCycles, openings: pytest.LogCaptureFixture, provider: str, outcome: str
) -> None:
    recorded = key_openings_of(openings, provider)
    assert recorded, "no opening of the key was recorded"
    message = recorded[-1].getMessage()
    tenant_id = flow_cycles.flow("alfa").tenant_id
    assert message.startswith(OUTCOMES[outcome]), message
    assert f"tenant {tenant_id.value}," in message
    assert flow_cycles.started_at <= recorded[-1].created <= time.time()


@then(quoted('la registrazione non contiene la chiave del fornitore "{provider}"'))
def register_without_key(openings: pytest.LogCaptureFixture, provider: str) -> None:
    recorded = key_openings_of(openings, provider)
    assert recorded, "no opening of the key was recorded"
    assert not [record for record in recorded if PROVIDER_KEY in f"{record.getMessage()} {vars(record)}"]
