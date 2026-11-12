from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal

from autotrading.domain.flows.cycle_interval import CycleInterval
from autotrading.domain.flows.errors import AllocatedCapitalNotPositiveError, AssetsRequiredError, RepeatedSourceError
from autotrading.domain.flows.risk_limits import RiskLimits
from autotrading.domain.flows.selections import ModelSelection, SourceSelection


def assets_of(names: Iterable[str]) -> tuple[str, ...]:
    """The assets in upper case, each once, in the order given."""
    assets = tuple(dict.fromkeys(name.strip().upper() for name in names if name.strip()))
    if not assets:
        raise AssetsRequiredError
    return assets


@dataclass(frozen=True, slots=True)
class FlowConfiguration:
    """One immutable, numbered version of what a flow does (R1.1.1, R1.1.3)."""

    version: int
    assets: tuple[str, ...]
    cycle_interval: CycleInterval
    model: ModelSelection
    sources: tuple[SourceSelection, ...]
    instructions: str
    risk_limits: RiskLimits
    allocated_capital: Decimal

    def __post_init__(self) -> None:
        if not self.assets:
            raise AssetsRequiredError
        names = [source.name for source in self.sources]
        repeated = next((name for name in names if names.count(name) > 1), None)
        if repeated is not None:
            raise RepeatedSourceError(repeated)
        if not self.allocated_capital.is_finite() or self.allocated_capital <= 0:
            raise AllocatedCapitalNotPositiveError
