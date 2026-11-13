"""Fakes of the ports on provider keys: the seal, the database, the flows using them."""

import hashlib

from autotrading.application.agent.errors import (
    ProviderKeyAlreadyRegisteredError,
    ProviderKeyNotFoundError,
    ProviderKeyNotOpenedError,
)
from autotrading.application.agent.ports import ModelUse
from autotrading.application.tenancy.errors import CrossTenantAccessError
from autotrading.domain.agent.provider_key import ProviderKey
from autotrading.domain.agent.provider_name import ProviderName
from autotrading.domain.agent.registered_provider_key import RegisteredProviderKey
from autotrading.domain.agent.sealed_provider_key import SealedProviderKey
from autotrading.domain.tenancy.tenant_id import TenantId

KEY_VERSION = 1

# What the private key would recover from each sealed text: only the worker would read it.
type ProviderKeyVault = dict[bytes, tuple[TenantId, ProviderName, ProviderKey]]


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

    def has_key(self, provider: ProviderName) -> bool:
        """The flows context asks only whether the tenant can use the provider (R1.4.1)."""
        return self.get(provider) is not None

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
    """The flows of a tenant with the provider of their model, as a test sets them."""

    def __init__(self) -> None:
        self.uses: list[ModelUse] = []

    def model_uses(self) -> tuple[ModelUse, ...]:
        return tuple(self.uses)


class FakeProviderKeyOpenerAdapter:
    """Recovers from the vault what the private key would: only a key sealed for its own tenant and provider."""

    def __init__(self, vault: ProviderKeyVault) -> None:
        self._vault = vault

    def open(self, key: RegisteredProviderKey) -> ProviderKey:
        tenant_id, provider, secret = self._vault.get(key.sealed.ciphertext, (None, None, None))
        if (tenant_id, provider) != (key.tenant_id, key.provider) or secret is None:
            raise ProviderKeyNotOpenedError(key.provider)
        return secret
