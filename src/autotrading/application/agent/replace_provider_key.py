from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date

from autotrading.application.agent.model_gateways import joined_catalog
from autotrading.application.agent.ports import ProviderKeyRegistration, ProviderKeyRepositoryPort
from autotrading.application.agent.provider_keys import (
    entered_expiry,
    operations,
    registered_key,
    supported_provider,
)
from autotrading.application.agent.register_provider_key import ProviderKeyServices
from autotrading.domain.agent.provider_key import ProviderKey
from autotrading.domain.agent.registered_provider_key import RegisteredProviderKey


@dataclass(frozen=True, slots=True)
class ReplaceProviderKeyCommand:
    provider: str
    key: Mapping[str, str] = field(repr=False)
    # The day the key stops working, given only when no gateway reads it (R6.2.2).
    expires_on: date | None = None


class ReplaceProviderKeyUseCase:
    """Puts a new key in place of the one of a provider (R1.4.1).

    The next cycles of the flows use the new key: the worker opens the key at every cycle. The expiry of the old key
    goes with it: the new one carries the date the user gave with it, or none (R6.2.2).
    """

    def __init__(self, keys: ProviderKeyRepositoryPort, services: ProviderKeyServices) -> None:
        self._keys = keys
        self._services = services

    def execute(self, command: ReplaceProviderKeyCommand) -> ProviderKeyRegistration:
        provider = supported_provider(self._services.catalogs, command.provider)
        key = ProviderKey.declared(joined_catalog(self._services.catalogs).key_fields_of(provider), command.key)
        expiry = entered_expiry(self._services.catalogs, provider, command.expires_on)
        current = registered_key(self._keys, provider)
        sealed = self._services.sealer.seal(provider, key)
        replacement = self._keys.replace(RegisteredProviderKey(current.tenant_id, provider, sealed, expiry))
        operations.info("chiave del fornitore sostituita", extra={"provider": provider.value})
        return replacement
