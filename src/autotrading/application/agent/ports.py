from typing import Protocol

from autotrading.domain.agent.provider_key import ProviderKey
from autotrading.domain.agent.provider_name import ProviderName
from autotrading.domain.agent.registered_provider_key import RegisteredProviderKey
from autotrading.domain.agent.sealed_provider_key import SealedProviderKey


class ProviderKeyVerifierPort(Protocol):
    def verify(self, provider: ProviderName, key: ProviderKey) -> None:
        """Asks the provider whether it accepts the key, without spending any credit of the user.

        Raises ProviderRejectedKeyError, ProviderUnavailableError, or ProviderNotVerifiableError.
        """
        ...


class ProviderKeySealerPort(Protocol):
    """Bound to the tenant of the request: the sealed text names tenant and provider (ADR 0029)."""

    def seal(self, provider: ProviderName, key: ProviderKey) -> SealedProviderKey: ...


class ProviderKeyRepositoryPort(Protocol):
    """Bound to the tenant of the request: it never sees the keys of another tenant."""

    def list(self) -> list[RegisteredProviderKey]: ...

    def get(self, provider: ProviderName) -> RegisteredProviderKey | None: ...

    def add(self, key: RegisteredProviderKey) -> None:
        """Raises ProviderKeyAlreadyRegisteredError when the tenant already has a key for that provider."""
        ...

    def replace(self, key: RegisteredProviderKey) -> None:
        """Raises ProviderKeyNotFoundError when the tenant has no key for that provider."""
        ...

    def remove(self, provider: ProviderName) -> None:
        """Raises ProviderKeyNotFoundError when the tenant has no key for that provider."""
        ...


class ProviderKeyUsagePort(Protocol):
    """Bound to the tenant of the request."""

    def flows_using(self, provider: ProviderName) -> list[str]:
        """The names of the active or paused flows whose model belongs to the provider."""
        ...
