from dataclasses import dataclass
from datetime import date, datetime

from autotrading.application.agent.model_gateways import ModelCatalogs
from autotrading.application.agent.ports import ProviderKeyRegistration
from autotrading.application.agent.provider_keys import expiry_editable
from autotrading.domain.agent.key_expiry import KeyExpiry, KeyExpiryReading, expiry_reading_of
from autotrading.domain.agent.provider_name import ProviderName


@dataclass(frozen=True, slots=True)
class ProviderKeySummary:
    """A key as its owner reads it on the page of the keys on a day: the provider, when it was saved (ADR 0130), the
    expiry and who gave it, its state with the days left, and whether the user may give the date (R6.2.2).
    """

    provider: ProviderName
    registered_at: datetime
    expiry: KeyExpiry | None
    reading: KeyExpiryReading
    expiry_editable: bool

    @classmethod
    def of(cls, registration: ProviderKeyRegistration, catalogs: ModelCatalogs, today: date) -> ProviderKeySummary:
        return cls(
            registration.provider,
            registration.registered_at,
            registration.expiry,
            expiry_reading_of(registration.expiry, today),
            expiry_editable(catalogs, registration.provider),
        )
