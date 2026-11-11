from dataclasses import dataclass

from autotrading.application.agent.errors import ProviderKeyInUseError
from autotrading.application.agent.ports import ProviderKeyRepositoryPort, ProviderKeyUsagePort
from autotrading.application.agent.provider_keys import operations, registered_key
from autotrading.domain.agent.provider_name import ProviderName


@dataclass(frozen=True, slots=True)
class RemoveProviderKeyCommand:
    provider: str


class RemoveProviderKeyUseCase:
    """Deletes the key of a provider, unless an active or paused flow still uses that provider (R1.4.1)."""

    def __init__(self, keys: ProviderKeyRepositoryPort, usage: ProviderKeyUsagePort) -> None:
        self._keys = keys
        self._usage = usage

    def execute(self, command: RemoveProviderKeyCommand) -> None:
        provider = registered_key(self._keys, ProviderName(command.provider)).provider
        self._require_unused(provider)
        self._keys.remove(provider)
        operations.info("chiave del fornitore rimossa", extra={"provider": provider.value})

    def _require_unused(self, provider: ProviderName) -> None:
        flows = self._usage.flows_using(provider)
        if flows:
            raise ProviderKeyInUseError(flows)
