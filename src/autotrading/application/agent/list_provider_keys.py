from autotrading.application.agent.ports import ProviderKeyRepositoryPort
from autotrading.domain.agent.provider_name import ProviderName


class ListProviderKeysUseCase:
    """The providers the tenant has a key for: the keys themselves never leave the database (R1.4.1)."""

    def __init__(self, keys: ProviderKeyRepositoryPort) -> None:
        self._keys = keys

    def execute(self) -> list[ProviderName]:
        return sorted((key.provider for key in self._keys.list()), key=lambda provider: provider.value)
