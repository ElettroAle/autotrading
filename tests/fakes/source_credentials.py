"""Fakes of the ports on the credentials of the adapters of the sources: the seal, the database, the notice of a
refusal (R4.1.2)."""

import hashlib
import json
from collections.abc import Mapping
from datetime import UTC, datetime

from autotrading.application.sources.errors import SourceCredentialsNotFoundError, SourceSecretsNotOpenedError
from autotrading.application.sources.ports import SourceCredentialsRegistration
from autotrading.application.tenancy.errors import CrossTenantAccessError
from autotrading.domain.sources.key_expiry import KeyExpiry
from autotrading.domain.sources.sealed_source_secrets import SealedSourceSecrets
from autotrading.domain.sources.source_credentials import SourceCredentials
from autotrading.domain.tenancy.tenant_id import TenantId

KEY_VERSION = 1

# What the private key would recover from each sealed text: only the worker would read it.
type SourceSecretsVault = dict[bytes, tuple[TenantId, str, dict[str, str]]]


class FakeSourceSecretsSealerAdapter:
    """Seals into an opaque digest bound to tenant and adapter; nothing readable survives, as with the real key."""

    def __init__(self, tenant_id: TenantId, vault: SourceSecretsVault | None = None) -> None:
        self._tenant_id = tenant_id
        self._vault: SourceSecretsVault = {} if vault is None else vault

    def seal(self, adapter: str, secrets: Mapping[str, str]) -> SealedSourceSecrets:
        material = json.dumps([str(self._tenant_id.value), adapter, dict(secrets)], sort_keys=True)
        ciphertext = hashlib.sha256(material.encode()).digest()
        self._vault[ciphertext] = (self._tenant_id, adapter, dict(secrets))
        return SealedSourceSecrets(KEY_VERSION, ciphertext)


class FakeSourceSecretsOpenerAdapter:
    """Recovers from the vault what the private key would: only secrets sealed for their own tenant and adapter."""

    def __init__(self, vault: SourceSecretsVault) -> None:
        self._vault = vault
        self.opened: list[str] = []

    def open(self, credentials: SourceCredentials) -> Mapping[str, str]:
        tenant_id, adapter, secrets = self._vault.get(credentials.sealed.ciphertext, (None, None, None))
        if (tenant_id, adapter) != (credentials.tenant_id, credentials.adapter) or secrets is None:
            raise SourceSecretsNotOpenedError(credentials.adapter)
        self.opened.append(credentials.adapter)
        return secrets


class SourceCredentialsStore:
    """The credentials of every tenant, as the database holds them, each stamped with the clock of the database."""

    def __init__(self) -> None:
        self.credentials: list[SourceCredentials] = []
        self.now = datetime(2026, 11, 14, 9, 0, tzinfo=UTC)
        self.saved_at: dict[tuple[TenantId, str], datetime] = {}

    def of(self, tenant_id: TenantId) -> list[SourceCredentials]:
        return sorted((each for each in self.credentials if each.tenant_id == tenant_id), key=lambda each: each.adapter)


class InMemorySourceCredentialsRepositoryAdapter:
    """Bound to one tenant, like the real adapter under row level security; it also tells the flows which adapters
    the tenant configured (R4.1.2)."""

    def __init__(self, store: SourceCredentialsStore, tenant_id: TenantId) -> None:
        self._store = store
        self._tenant_id = tenant_id

    def registrations(self) -> tuple[SourceCredentialsRegistration, ...]:
        return tuple(
            SourceCredentialsRegistration(each, self._store.saved_at[(each.tenant_id, each.adapter)])
            for each in self._store.of(self._tenant_id)
        )

    def configured_adapters(self) -> frozenset[str]:
        return frozenset(each.adapter for each in self._store.of(self._tenant_id))

    def get(self, adapter: str) -> SourceCredentials | None:
        return next((each for each in self._store.of(self._tenant_id) if each.adapter == adapter), None)

    def save(self, credentials: SourceCredentials) -> None:
        if credentials.tenant_id != self._tenant_id:
            raise CrossTenantAccessError
        current = self.get(credentials.adapter)
        if current is not None:
            self._store.credentials.remove(current)
        self._store.credentials.append(credentials)
        self._store.saved_at[(self._tenant_id, credentials.adapter)] = self._store.now

    def remove(self, adapter: str) -> None:
        self._store.credentials.remove(self._required(adapter))

    def set_expiry(self, adapter: str, expiry: KeyExpiry | None) -> None:
        self._replace(self._required(adapter).with_expiry(expiry))

    def mark_rejected(self, adapter: str, at: datetime) -> bool:
        current = self.get(adapter)
        if current is None or current.was_rejected:
            return False
        self._replace(current.rejected(at))
        return True

    def _replace(self, credentials: SourceCredentials) -> None:
        current = self._required(credentials.adapter)
        self._store.credentials[self._store.credentials.index(current)] = credentials

    def _required(self, adapter: str) -> SourceCredentials:
        current = self.get(adapter)
        if current is None:
            raise SourceCredentialsNotFoundError(adapter)
        return current


class FakeSourceCredentialsRejectionNoticeAdapter:
    """Remembers the adapters whose credentials the user was told were refused."""

    def __init__(self) -> None:
        self.told: list[str] = []

    def execute(self, adapter: str) -> None:
        self.told.append(adapter)


class FakeConfiguredSourceAdaptersAdapter:
    """The adapters the tenant configured, as a test sets them (R4.1.2)."""

    def __init__(self, configured: frozenset[str] = frozenset()) -> None:
        self.configured = configured

    def configured_adapters(self) -> frozenset[str]:
        return self.configured
