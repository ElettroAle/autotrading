from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field, replace
from datetime import datetime
from types import MappingProxyType

from autotrading.domain.sources.errors import (
    SourceConfigurationFieldRequiredError,
    UnknownSourceConfigurationFieldError,
)
from autotrading.domain.sources.key_expiry import KeyExpiry
from autotrading.domain.sources.sealed_source_secrets import SealedSourceSecrets
from autotrading.domain.sources.source_adapter_declaration import SourceConfigurationField
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.tenant_owned import TenantOwned

MASK = "***"


@dataclass(frozen=True, slots=True)
class SourceConfigurationValues:
    """The values the user gives for the fields an adapter of a source declares, split by the declaration: the public
    ones are shown back, the secret ones are sealed and never shown in clear (R4.1.2).
    """

    public: Mapping[str, str]
    secrets: Mapping[str, str] = field(repr=False)

    @classmethod
    def declared(
        cls, fields: Iterable[SourceConfigurationField], values: Mapping[str, str]
    ) -> SourceConfigurationValues:
        """Every declared field is required; a field the adapter does not declare is refused by its name."""
        declared = tuple(fields)
        names = {configuration_field.name for configuration_field in declared}
        unknown = sorted(name for name in values if name not in names)
        if unknown:
            raise UnknownSourceConfigurationFieldError(unknown[0])
        given = [(configuration_field, _required(configuration_field, values)) for configuration_field in declared]
        return cls(
            MappingProxyType({each.name: value for each, value in given if not each.secret}),
            MappingProxyType({each.name: value for each, value in given if each.secret}),
        )

    def __repr__(self) -> str:
        return f"SourceConfigurationValues(public={dict(self.public)}, secrets={MASK})"

    __str__ = __repr__


@dataclass(frozen=True, slots=True)
class SourceCredentials(TenantOwned):
    """The credentials a tenant gave an adapter of a source, once for all its flows: the public values in clear, the
    secret ones sealed, readable only by the worker (R4.1.2, ADR 0007, ADR credenziali-degli-adapter-delle-fonti).

    The provider may refuse them in a cycle: the instant of the first refusal is kept until they are replaced.
    """

    tenant_id: TenantId
    adapter: str
    public_values: Mapping[str, str]
    sealed: SealedSourceSecrets
    # None while the expiry of the credentials is unknown (R6.2.2).
    expiry: KeyExpiry | None = None
    rejected_at: datetime | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "public_values", MappingProxyType(dict(self.public_values)))

    @property
    def was_rejected(self) -> bool:
        return self.rejected_at is not None

    def rejected(self, at: datetime) -> SourceCredentials:
        return replace(self, rejected_at=at)

    def with_expiry(self, expiry: KeyExpiry | None) -> SourceCredentials:
        """The day the credentials stop working, given by the user (R6.2.2)."""
        return replace(self, expiry=expiry)


def _required(configuration_field: SourceConfigurationField, values: Mapping[str, str]) -> str:
    value = values.get(configuration_field.name, "").strip()
    if not value:
        raise SourceConfigurationFieldRequiredError(configuration_field.name, configuration_field.label)
    return value
