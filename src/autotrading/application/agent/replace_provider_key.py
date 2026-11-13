from dataclasses import dataclass, field

from autotrading.application.agent.ports import ProviderKeyRepositoryPort
from autotrading.application.agent.provider_keys import operations, registered_key, supported_provider
from autotrading.application.agent.register_provider_key import ProviderKeyServices
from autotrading.domain.agent.provider_key import ProviderKey
from autotrading.domain.agent.provider_name import ProviderName
from autotrading.domain.agent.registered_provider_key import RegisteredProviderKey


@dataclass(frozen=True, slots=True)
class ReplaceProviderKeyCommand:
    provider: str
    key: str = field(repr=False)


class ReplaceProviderKeyUseCase:
    """Puts a new key in place of the one of a provider (R1.4.1).

    The next cycles of the flows use the new key: the worker opens the key at every cycle.
    """

    def __init__(self, keys: ProviderKeyRepositoryPort, services: ProviderKeyServices) -> None:
        self._keys = keys
        self._services = services

    def execute(self, command: ReplaceProviderKeyCommand) -> ProviderName:
        provider = supported_provider(self._services.gateways, command.provider)
        key = ProviderKey(command.key)
        current = registered_key(self._keys, provider)
        sealed = self._services.sealer.seal(provider, key)
        self._keys.replace(RegisteredProviderKey(current.tenant_id, provider, sealed))
        operations.info("chiave del fornitore sostituita", extra={"provider": provider.value})
        return provider
