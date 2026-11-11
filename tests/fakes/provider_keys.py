"""Fakes of the ports on provider keys: the provider that checks them, the seal, the database, the flows using them."""

import hashlib

from autotrading.application.agent.errors import (
    ProviderKeyAlreadyRegisteredError,
    ProviderKeyNotFoundError,
    ProviderRejectedKeyError,
    ProviderUnavailableError,
)
from autotrading.application.tenancy.errors import CrossTenantAccessError
from autotrading.domain.agent.provider_key import ProviderKey
from autotrading.domain.agent.provider_name import ProviderName
from autotrading.domain.agent.registered_provider_key import RegisteredProviderKey
from autotrading.domain.agent.sealed_provider_key import SealedProviderKey
from autotrading.domain.tenancy.tenant_id import TenantId

KEY_VERSION = 1

# What the private key would recover from each sealed text: only the worker would read it.
type ProviderKeyVault = dict[bytes, tuple[TenantId, ProviderName, ProviderKey]]


class FakeProviderKeyVerifierAdapter:
    """The providers: each accepts the keys it was told to, and may be out of reach."""

    def __init__(self) -> None:
        self._accepted: dict[ProviderName, set[str]] = {}
        self.unreachable: set[ProviderName] = set()
        self.checked: list[ProviderName] = []

    def accept(self, provider: str, key: str) -> None:
        self._accepted.setdefault(ProviderName(provider), set()).add(key)

    def refuse(self, provider: str, key: str) -> None:
        self._accepted.get(ProviderName(provider), set()).discard(key)

    def verify(self, provider: ProviderName, key: ProviderKey) -> None:
        self.checked.append(provider)
        if provider in self.unreachable:
            raise ProviderUnavailableError(provider)
        if key.secret not in self._accepted.get(provider, set()):
            raise ProviderRejectedKeyError(provider)


class FakeProviderKeySealerAdapter:
    """Seals into an opaque digest bound to tenant and provider; nothing readable survives, as with the real key."""

    def __init__(self, tenant_id: TenantId, vault: ProviderKeyVault | None = None) -> None:
        self._tenant_id = tenant_id
        self._vault: ProviderKeyVault = {} if vault is None else vault

    def seal(self, provider: ProviderName, key: ProviderKey) -> SealedProviderKey:
        material = f"{self._tenant_id.value}|{provider.value}|{key.secret}"
        ciphertext = hashlib.sha256(material.encode()).digest()
        self._vault[ciphertext] = (self._tenant_id, provider, key)
        return SealedProviderKey(KEY_VERSION, ciphertext)


class ProviderKeyStore:
    """The keys of every tenant, as the database holds them."""

    def __init__(self) -> None:
        self.keys: list[RegisteredProviderKey] = []

    def of(self, tenant_id: TenantId) -> list[RegisteredProviderKey]:
        return [key for key in self.keys if key.tenant_id == tenant_id]


class InMemoryProviderKeyRepositoryAdapter:
    """Bound to one tenant, like the real adapter under row level security."""

    def __init__(self, store: ProviderKeyStore, tenant_id: TenantId) -> None:
        self._store = store
        self._tenant_id = tenant_id

    def list(self) -> list[RegisteredProviderKey]:
        return sorted(self._store.of(self._tenant_id), key=lambda key: key.provider.value)

    def get(self, provider: ProviderName) -> RegisteredProviderKey | None:
        return next((key for key in self.list() if key.provider == provider), None)

    def add(self, key: RegisteredProviderKey) -> None:
        self._require_own(key)
        if self.get(key.provider) is not None:
            raise ProviderKeyAlreadyRegisteredError(key.provider)
        self._store.keys.append(key)

    def replace(self, key: RegisteredProviderKey) -> None:
        self._require_own(key)
        current = self.get(key.provider)
        if current is None:
            raise ProviderKeyNotFoundError(key.provider)
        self._store.keys[self._store.keys.index(current)] = key

    def remove(self, provider: ProviderName) -> None:
        current = self.get(provider)
        if current is None:
            raise ProviderKeyNotFoundError(provider)
        self._store.keys.remove(current)

    def _require_own(self, key: RegisteredProviderKey) -> None:
        if key.tenant_id != self._tenant_id:
            raise CrossTenantAccessError


class FakeProviderKeyUsageAdapter:
    """The active or paused flows of a tenant, by provider of their model."""

    def __init__(self) -> None:
        self.flows: dict[ProviderName, list[str]] = {}

    def flows_using(self, provider: ProviderName) -> list[str]:
        return list(self.flows.get(provider, []))
