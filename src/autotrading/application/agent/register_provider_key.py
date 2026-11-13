from dataclasses import dataclass, field

from autotrading.application.agent.errors import ProviderKeyAlreadyRegisteredError
from autotrading.application.agent.ports import (
    ModelCatalogPort,
    ProviderKeyRepositoryPort,
    ProviderKeySealerPort,
)
from autotrading.application.agent.provider_keys import operations, supported_provider
from autotrading.domain.agent.provider_key import ProviderKey
from autotrading.domain.agent.provider_name import ProviderName
from autotrading.domain.agent.registered_provider_key import RegisteredProviderKey
from autotrading.domain.tenancy.tenant_id import TenantId


@dataclass(frozen=True, slots=True)
class RegisterProviderKeyCommand:
    provider: str
    key: str = field(repr=False)


@dataclass(frozen=True, slots=True)
class ProviderKeyServices:
    """What a use case needs to accept a key: the models offered and the seal.

    The provider is not asked about the key: a key it refuses comes out at the first cycle (R1.2.4).
    """

    catalog: ModelCatalogPort
    sealer: ProviderKeySealerPort


class RegisterProviderKeyUseCase:
    """Saves the key of a provider for the tenant, sealed (R1.4.1)."""

    def __init__(self, tenant_id: TenantId, keys: ProviderKeyRepositoryPort, services: ProviderKeyServices) -> None:
        self._tenant_id = tenant_id
        self._keys = keys
        self._services = services

    def execute(self, command: RegisterProviderKeyCommand) -> ProviderName:
        provider = supported_provider(self._services.catalog, command.provider)
        key = ProviderKey(command.key)
        self._require_none_for(provider)
        self._keys.add(RegisteredProviderKey(self._tenant_id, provider, self._services.sealer.seal(provider, key)))
        operations.info("chiave del fornitore registrata", extra={"provider": provider.value})
        return provider

    def _require_none_for(self, provider: ProviderName) -> None:
        if self._keys.get(provider) is not None:
            raise ProviderKeyAlreadyRegisteredError(provider)
