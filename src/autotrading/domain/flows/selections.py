from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal

from autotrading.domain.flows.errors import (
    ModelRequiredError,
    RepeatedSourceAdapterError,
    SourceAdapterRequiredError,
    SourceNotSelectedError,
    SourceWeightOutOfRangeError,
)

MINIMUM_WEIGHT = 1
MAXIMUM_WEIGHT = 10
DEFAULT_WEIGHT = 5
ADAPTER_SEPARATOR = " · "

type ModelParameterValue = Decimal | str
# A parameter of an adapter of a source: a whole number, or a list of them (ADR
# parametri-delle-fonti-come-liste-libere).
type AdapterParameterValue = int | tuple[int, ...]


@dataclass(frozen=True, slots=True)
class ModelSelection:
    """The model of the flow with every parameter resolved, defaults included (R1.4.2)."""

    name: str
    parameters: Mapping[str, ModelParameterValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ModelRequiredError


@dataclass(frozen=True, slots=True)
class ActiveSource:
    """An adapter of a source the flow activated: the cycle reads each one apart (R4.1.1, ADR 0105)."""

    source: str
    adapter: str

    @property
    def label(self) -> str:
        """How the agent, the record and the user read it: the source and its adapter."""
        return f"{self.source}{ADAPTER_SEPARATOR}{self.adapter}"


@dataclass(frozen=True, slots=True)
class AdapterSelection:
    """An adapter of an active source, with its weight and every parameter resolved, defaults included (R4.1.1).

    The weight belongs to the adapter, checked by the source that selects it.
    """

    name: str
    weight: int = DEFAULT_WEIGHT
    parameters: Mapping[str, AdapterParameterValue] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SourceSelection:
    """An active source with the adapters the flow chose, at least one, each once (R1.3.2, R4.1.1)."""

    name: str
    adapters: tuple[AdapterSelection, ...]

    def __post_init__(self) -> None:
        if not self.adapters:
            raise SourceAdapterRequiredError(self.name)
        if any(not MINIMUM_WEIGHT <= adapter.weight <= MAXIMUM_WEIGHT for adapter in self.adapters):
            raise SourceWeightOutOfRangeError(self.name)
        names = [adapter.name for adapter in self.adapters]
        repeated = next((name for name in names if names.count(name) > 1), None)
        if repeated is not None:
            raise RepeatedSourceAdapterError(self.name, repeated)

    def adapter(self, name: str) -> AdapterSelection:
        """The adapter of the source with that name, as the configuration of the cycle selects it (R4.1.1)."""
        selection = next((adapter for adapter in self.adapters if adapter.name == name), None)
        if selection is None:
            raise SourceNotSelectedError(ActiveSource(self.name, name).label)
        return selection

    @property
    def active(self) -> tuple[ActiveSource, ...]:
        return tuple(ActiveSource(self.name, adapter.name) for adapter in self.adapters)
