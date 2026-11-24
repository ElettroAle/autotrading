from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from decimal import Decimal

from autotrading.domain.flows.cycle_interval import CycleInterval
from autotrading.domain.flows.errors import (
    AllocatedCapitalNotPositiveError,
    AssetsRequiredError,
    FlowAssignmentMissingError,
    MaxConsecutiveFailuresOutOfRangeError,
    MaxLossOutOfRangeError,
    RepeatedSourceError,
    SourceNotSelectedError,
)
from autotrading.domain.flows.flow_memory import FlowMemory
from autotrading.domain.flows.flow_setting import FlowSetting
from autotrading.domain.flows.memory_entry import AssetMemory
from autotrading.domain.flows.minimum_confidence import MinimumConfidence
from autotrading.domain.flows.openings_resume import OpeningsResume
from autotrading.domain.flows.protection_defaults import ProtectionDefaults
from autotrading.domain.flows.risk_check import RiskPolicy
from autotrading.domain.flows.risk_limits import RiskLimits
from autotrading.domain.flows.selections import ActiveSource, ModelSelection, SourceSelection
from autotrading.domain.flows.system_prompt import (
    DEFAULT_SYSTEM_PROMPT,
    PromptSubject,
    checked_system_prompt,
    rendered_system_prompt,
)

FEWEST_CONSECUTIVE_FAILURES = 1
MOST_CONSECUTIVE_FAILURES = 100
LOWEST_MAX_LOSS = Decimal("0.1")
HIGHEST_MAX_LOSS = Decimal(100)


def assets_of(names: Iterable[str]) -> tuple[str, ...]:
    """The assets in upper case, each once, in the order given."""
    assets = tuple(dict.fromkeys(name.strip().upper() for name in names if name.strip()))
    if not assets:
        raise AssetsRequiredError
    return assets


@dataclass(frozen=True, slots=True)
class FlowConfiguration:
    """One immutable, numbered version of what a flow does (R1.1.1, R1.1.3).

    Assets and allocated capital are missing only in the versions of a draft: the flow requires them out of draft
    (ADR 0124).
    """

    version: int
    assets: tuple[str, ...]
    cycle_interval: CycleInterval
    model: ModelSelection
    sources: tuple[SourceSelection, ...]
    instructions: str
    risk_limits: RiskLimits
    allocated_capital: Decimal | None
    # Off unless the user chooses it: an opening below the exchange minimum is blocked (R1.5.4).
    bring_to_minimum: bool = False
    # The default of the platform unless the user writes their own, so a flow follows the updates of the default
    # until then (R1.4.8).
    system_prompt: str | None = None
    # No maximum unless the user sets one: the flow keeps trying at every cycle (R3.2.4).
    max_consecutive_failures: int | None = None
    # No maximum loss unless the user sets one; suspended openings resume by hand unless the user chooses the next day
    # (R3.2.2).
    max_daily_loss_percent: Decimal | None = None
    max_drawdown_percent: Decimal | None = None
    openings_resume: OpeningsResume = OpeningsResume.MANUAL
    # A stop loss of 5% and no take profit unless the user chooses others; the existing flows got the same (R3.1.2).
    protection_defaults: ProtectionDefaults = field(default_factory=ProtectionDefaults)
    # None unless the user sets one: every opening goes on whatever the confidence of the agent (R3.1.4).
    minimum_confidence: MinimumConfidence | None = None
    # Off unless the user turns it on: the agent decides on the data of the cycle alone (R5.3.4).
    memory: FlowMemory = field(default_factory=FlowMemory)

    def __post_init__(self) -> None:
        names = [source.name for source in self.sources]
        repeated = next((name for name in names if names.count(name) > 1), None)
        if repeated is not None:
            raise RepeatedSourceError(repeated)
        capital = self.allocated_capital
        if capital is not None and (not capital.is_finite() or capital <= 0):
            raise AllocatedCapitalNotPositiveError
        if self.system_prompt is not None:
            checked_system_prompt(self.system_prompt)
        maximum = self.max_consecutive_failures
        if maximum is not None and not FEWEST_CONSECUTIVE_FAILURES <= maximum <= MOST_CONSECUTIVE_FAILURES:
            raise MaxConsecutiveFailuresOutOfRangeError
        _check_max_loss(self.max_daily_loss_percent, FlowSetting.MAX_DAILY_LOSS)
        _check_max_loss(self.max_drawdown_percent, FlowSetting.MAX_DRAWDOWN)

    @property
    def assigned_capital(self) -> Decimal:
        """The allocated capital of a configuration that has one: every flow out of draft (ADR 0124)."""
        if self.allocated_capital is None:
            raise FlowAssignmentMissingError(("capitale allocato",))
        return self.allocated_capital

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
    def active_sources(self) -> tuple[ActiveSource, ...]:
        """Every adapter of every active source, in the order of the configuration: the cycle reads each one
        (R4.1.1).
        """
        return tuple(active for source in self.sources for active in source.active)

    @property
    def system_prompt_template(self) -> str:
        """The template in force: the user's own, or the default of the platform (R1.4.8)."""
        return DEFAULT_SYSTEM_PROMPT if self.system_prompt is None else self.system_prompt

    def rendered_system_prompt(self, actions: tuple[str, ...], memory: tuple[AssetMemory, ...] | None = None) -> str:
        """The system prompt the agent receives, with the values of this configuration and the memory of the flow,
        None with the memory off (R1.4.8, R5.3.4).
        """
        return rendered_system_prompt(self.system_prompt_template, PromptSubject(self, actions, memory))

    @property
    def risk_policy(self) -> RiskPolicy:
        return RiskPolicy(self.risk_limits, self.bring_to_minimum, self.minimum_confidence)


def _check_max_loss(percent: Decimal | None, setting: FlowSetting) -> None:
    if percent is not None and not (percent.is_finite() and LOWEST_MAX_LOSS <= percent <= HIGHEST_MAX_LOSS):
        raise MaxLossOutOfRangeError(setting)
