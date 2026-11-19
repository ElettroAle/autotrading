from collections.abc import Collection
from dataclasses import dataclass

from autotrading.domain.sources.errors import InvalidSourceAdapterDeclarationError, SourceAdapterNotConfiguredError
from autotrading.domain.sources.source_parameter import SourceParameter


@dataclass(frozen=True, slots=True)
class SourceConfigurationField:
    """A value an adapter of a source needs from the user, such as a key; a secret one never comes back (R4.1.1)."""

    name: str
    label: str
    secret: bool


@dataclass(frozen=True, slots=True)
class SourceAdapterDeclaration:
    """What an adapter of a source declares of itself: the parameters of its own, beside those of the source, the
    fields of configuration it needs, none when it needs no configuration, and whether it offers historical data, which
    the replay reads (R4.1.1, ADR fonti-con-adapter-dichiarati).
    """

    name: str
    description: str
    parameters: tuple[SourceParameter, ...]
    configuration_fields: tuple[SourceConfigurationField, ...]
    offers_history: bool

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise InvalidSourceAdapterDeclarationError(self.name)
        names = [field.name for field in self.configuration_fields]
        repeated = next((name for name in names if names.count(name) > 1), None)
        if repeated is not None:
            raise InvalidSourceAdapterDeclarationError(self.name, repeated)

    @property
    def needs_configuration(self) -> bool:
        return bool(self.configuration_fields)

    def require_configured(self, configured: Collection[str]) -> None:
        """An adapter that needs configuration is activatable only once the tenant gave it (R4.1.2)."""
        if self.needs_configuration and self.name not in configured:
            raise SourceAdapterNotConfiguredError(self.name)

    def missing_configuration(self, configured: Collection[str]) -> str | None:
        """Why the adapter is not activatable for the tenant, none when it is (R4.1.2)."""
        if self.needs_configuration and self.name not in configured:
            return str(SourceAdapterNotConfiguredError(self.name))
        return None
