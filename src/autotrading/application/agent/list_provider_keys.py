from autotrading.application.agent.ports import ProviderKeyRegistration, ProviderKeyRepositoryPort


class ListProviderKeysUseCase:
    """The providers the tenant has a key for, with the instant of each: the keys never leave the database (R1.4.1)."""

    def __init__(self, keys: ProviderKeyRepositoryPort) -> None:
        self._keys = keys

    def execute(self) -> list[ProviderKeyRegistration]:
        return sorted(self._keys.registrations(), key=lambda registration: registration.provider.value)
