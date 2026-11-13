from collections.abc import Callable, Iterable
from dataclasses import dataclass
from decimal import Decimal

from autotrading.domain.flows.cycle_interval import CycleInterval
from autotrading.domain.flows.errors import (
    AllocatedCapitalNotPositiveError,
    AssetsRequiredError,
    RepeatedSourceError,
    SourceNotSelectedError,
)
from autotrading.domain.flows.risk_check import RiskPolicy
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
    # Off unless the user chooses it: an opening below the exchange minimum is blocked (R1.5.4).
    bring_to_minimum: bool = False

    def __post_init__(self) -> None:
        if not self.assets:
            raise AssetsRequiredError
        names = [source.name for source in self.sources]
        repeated = next((name for name in names if names.count(name) > 1), None)
        if repeated is not None:
            raise RepeatedSourceError(repeated)
        if not self.allocated_capital.is_finite() or self.allocated_capital <= 0:
            raise AllocatedCapitalNotPositiveError

    def covers(self, asset: str) -> bool:
        """The flow trades only its own assets: a position on another asset belongs to someone else."""
        return asset in self.assets

    def held[T](self, positions: Iterable[T], asset_of: Callable[[T], str]) -> tuple[T, ...]:
        """The positions of the account that belong to the flow: those on its assets."""
        return tuple(position for position in positions if self.covers(asset_of(position)))

    def source(self, name: str) -> SourceSelection:
        """The active source of the flow with that name, as the configuration of the cycle selects it (R1.3.2)."""
        selection = next((selected for selected in self.sources if selected.name == name), None)
        if selection is None:
            raise SourceNotSelectedError(name)
        return selection

    @property
    def risk_policy(self) -> RiskPolicy:
        return RiskPolicy(self.risk_limits, self.bring_to_minimum)
