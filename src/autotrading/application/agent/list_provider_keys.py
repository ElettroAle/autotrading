from collections.abc import Callable
from datetime import datetime

from autotrading.application.agent.model_gateways import ModelCatalogs
from autotrading.application.agent.ports import ProviderKeyRepositoryPort
from autotrading.application.agent.provider_key_summary import ProviderKeySummary
from autotrading.domain.agent.key_expiry import utc_day_of


class ListProviderKeysUseCase:
    """The providers the tenant has a key for, with the instant of each: the keys never leave the database (R1.4.1);
    and the expiry of each key as of today (R6.2.2).
    """

    def __init__(self, keys: ProviderKeyRepositoryPort, catalogs: ModelCatalogs, clock: Callable[[], datetime]) -> None:
        self._keys = keys
        self._catalogs = catalogs
        self._clock = clock

    def execute(self) -> list[ProviderKeySummary]:
        today = utc_day_of(self._clock())
        registrations = sorted(self._keys.registrations(), key=lambda registration: registration.provider.value)
        return [ProviderKeySummary.of(registration, self._catalogs, today) for registration in registrations]
