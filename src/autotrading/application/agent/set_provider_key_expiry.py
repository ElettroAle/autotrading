from dataclasses import dataclass
from datetime import date

from autotrading.application.agent.model_gateways import ModelCatalogs
from autotrading.application.agent.ports import ProviderKeyRepositoryPort
from autotrading.application.agent.provider_keys import entered_expiry, operations, registered_key
from autotrading.domain.agent.provider_name import ProviderName


@dataclass(frozen=True, slots=True)
class SetProviderKeyExpiryCommand:
    provider: str
    # None forgets the date: the expiry is unknown again.
    expires_on: date | None


class SetProviderKeyExpiryUseCase:
    """Keeps the day the user says the key of a provider stops working, or forgets it, when no gateway reads it (R6.2.2,
    ADR scadenza-delle-chiavi-letta-o-indicata).

    A new date is a new expiry: the notices of the old one do not count for it (R6.2.2).
    """

    def __init__(self, keys: ProviderKeyRepositoryPort, catalogs: ModelCatalogs) -> None:
        self._keys = keys
        self._catalogs = catalogs

    def execute(self, command: SetProviderKeyExpiryCommand) -> None:
        provider = registered_key(self._keys, ProviderName(command.provider)).provider
        self._keys.set_expiry(provider, entered_expiry(self._catalogs, provider, command.expires_on))
        operations.info("scadenza della chiave indicata", extra={"provider": provider.value})
