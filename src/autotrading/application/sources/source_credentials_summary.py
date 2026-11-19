from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
from types import MappingProxyType

from autotrading.application.sources.ports import SourceCredentialsRegistration
from autotrading.domain.sources.key_expiry import KeyExpiry, KeyExpiryReading, expiry_reading_of
from autotrading.domain.sources.source_adapter_declaration import SourceConfigurationField
from autotrading.domain.sources.source_catalog import ConfigurableAdapter

# No adapter of a source reads the expiry of its credentials today: the user gives it (ADR
# credenziali-degli-adapter-delle-fonti).
EXPIRY_EDITABLE = True


@dataclass(frozen=True, slots=True)
class SourceCredentialsSummary:
    """An adapter that needs configuration as its owner reads it on the page of the keys on a day: the sources it
    offers, the fields it declares, whether the tenant configured it, the public values and when they were saved, the
    expiry with its state, and whether the provider refused the credentials; never a secret (R4.1.2, R6.2.2).
    """

    adapter: str
    sources: tuple[str, ...]
    fields: tuple[SourceConfigurationField, ...]
    registration: SourceCredentialsRegistration | None
    reading: KeyExpiryReading
    expiry_editable: bool = EXPIRY_EDITABLE

    @classmethod
    def of(
        cls, adapter: ConfigurableAdapter, registration: SourceCredentialsRegistration | None, today: date
    ) -> SourceCredentialsSummary:
        expiry = None if registration is None else registration.credentials.expiry
        return cls(
            adapter.name,
            adapter.sources,
            adapter.declaration.configuration_fields,
            registration,
            expiry_reading_of(expiry, today),
        )

    @property
    def configured(self) -> bool:
        return self.registration is not None

    @property
    def public_values(self) -> Mapping[str, str]:
        if self.registration is None:
            return MappingProxyType({})
        return self.registration.credentials.public_values

    @property
    def registered_at(self) -> datetime | None:
        return None if self.registration is None else self.registration.registered_at

    @property
    def expiry(self) -> KeyExpiry | None:
        return None if self.registration is None else self.registration.credentials.expiry

    @property
    def rejected(self) -> bool:
        return self.registration is not None and self.registration.credentials.was_rejected
