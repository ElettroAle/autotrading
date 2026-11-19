from dataclasses import dataclass

from autotrading.domain.sources.errors import InvalidSourceAdapterDeclarationError
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
