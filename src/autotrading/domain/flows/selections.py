from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal

from autotrading.domain.flows.errors import ModelRequiredError, SourceWeightOutOfRangeError

MINIMUM_WEIGHT = 1
MAXIMUM_WEIGHT = 10
DEFAULT_WEIGHT = 5

type ModelParameterValue = Decimal | str


@dataclass(frozen=True, slots=True)
class ModelSelection:
    """The model of the flow with every parameter resolved, defaults included (R1.4.2)."""

    name: str
    parameters: Mapping[str, ModelParameterValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ModelRequiredError


@dataclass(frozen=True, slots=True)
class SourceSelection:
    """An active source with its weight and every parameter resolved, defaults included (R1.3.2)."""

    name: str
    weight: int = DEFAULT_WEIGHT
    parameters: Mapping[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not MINIMUM_WEIGHT <= self.weight <= MAXIMUM_WEIGHT:
            raise SourceWeightOutOfRangeError(self.name)
