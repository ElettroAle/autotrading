from dataclasses import dataclass, field
from decimal import Decimal

from autotrading.domain.flows.consecutive_loss_limit import ConsecutiveLossLimit
from autotrading.domain.flows.cycle_interval import CycleInterval
from autotrading.domain.flows.errors import StrategyModelMissingError
from autotrading.domain.flows.flow_configuration import FlowConfiguration
from autotrading.domain.flows.flow_memory import FlowMemory
from autotrading.domain.flows.minimum_confidence import MinimumConfidence
from autotrading.domain.flows.openings_resume import OpeningsResume
from autotrading.domain.flows.protection_defaults import ProtectionDefaults
from autotrading.domain.flows.risk_limits import RiskLimits
from autotrading.domain.flows.selections import ModelSelection, SourceSelection
from autotrading.domain.flows.trailing_stop import TrailingStop


@dataclass(frozen=True, slots=True)
class FlowStrategy:
    """What a flow does, without where and with how much: the part of a configuration a strategy file carries.

    Interval, sources with weights and parameters, model with its parameters, instructions, risk rules, protection, the
    stop that follows the price, the limit of consecutive losses and memory; account, allocated capital and assets
    belong to the flow that uses the strategy, assigned to its draft (R2.5.2, ADR 0140, R5.3.4, R5.5.1, R5.5.2).
    """

    cycle_interval: CycleInterval
    model: ModelSelection
    sources: tuple[SourceSelection, ...]
    instructions: str
    risk_limits: RiskLimits
    # Off unless the user chooses it, as in the configuration: a risk rule like the limits (R1.5.4).
    bring_to_minimum: bool = False
    # The default of the platform unless the strategy has its own, as in the configuration (R1.4.8).
    system_prompt: str | None = None
    # No maximum unless the strategy has one, as in the configuration (R3.2.4).
    max_consecutive_failures: int | None = None
    # No maximum loss and the manual resume unless the strategy has its own, as in the configuration (R3.2.2).
    max_daily_loss_percent: Decimal | None = None
    max_drawdown_percent: Decimal | None = None
    openings_resume: OpeningsResume = OpeningsResume.MANUAL
    # The protection of every opening, a risk rule like the limits (R3.1.2).
    protection_defaults: ProtectionDefaults = field(default_factory=ProtectionDefaults)
    # The confidence an opening needs, a risk rule like the limits; none unless the strategy has one (R3.1.4).
    minimum_confidence: MinimumConfidence | None = None
    # How the agent remembers its decisions, off unless the strategy has it on, as in the configuration (R5.3.4).
    memory: FlowMemory = field(default_factory=FlowMemory)
    # How the stop follows the price, a risk rule like the protection; empty unless the strategy has it (R5.5.1).
    trailing_stop: TrailingStop = field(default_factory=TrailingStop)
    # A risk rule like the maximum loss; none unless the strategy has it (R5.5.2).
    consecutive_loss_limit: ConsecutiveLossLimit | None = None
    # What the agent sees of the account, off unless the strategy has it on (R5.5.5).
    account_exposure_for_agent: bool = False
    # What the agent sees of the fees of the account, off unless the strategy has it on (R5.5.6).
    fees_for_agent: bool = False

    @classmethod
    def of(cls, configuration: FlowConfiguration) -> FlowStrategy:
        return cls(
            configuration.cycle_interval,
            configuration.model,
            configuration.sources,
            configuration.instructions,
            configuration.risk_limits,
            configuration.bring_to_minimum,
            configuration.system_prompt,
            configuration.max_consecutive_failures,
            configuration.max_daily_loss_percent,
            configuration.max_drawdown_percent,
            configuration.openings_resume,
            configuration.protection_defaults,
            configuration.minimum_confidence,
            configuration.memory,
            configuration.trailing_stop,
            configuration.consecutive_loss_limit,
            configuration.account_exposure_for_agent,
            configuration.fees_for_agent,
        )

    def draft_configuration(self, version: int) -> FlowConfiguration:
        """The configuration of a draft with this strategy: no assets and no capital until they are assigned."""
        return FlowConfiguration(
            version=version,
            assets=(),
            cycle_interval=self.cycle_interval,
            model=self.model,
            sources=self.sources,
            instructions=self.instructions,
            risk_limits=self.risk_limits,
            allocated_capital=None,
            bring_to_minimum=self.bring_to_minimum,
            system_prompt=self.system_prompt,
            max_consecutive_failures=self.max_consecutive_failures,
            max_daily_loss_percent=self.max_daily_loss_percent,
            max_drawdown_percent=self.max_drawdown_percent,
            openings_resume=self.openings_resume,
            protection_defaults=self.protection_defaults,
            minimum_confidence=self.minimum_confidence,
            memory=self.memory,
            trailing_stop=self.trailing_stop,
            consecutive_loss_limit=self.consecutive_loss_limit,
            account_exposure_for_agent=self.account_exposure_for_agent,
            fees_for_agent=self.fees_for_agent,
        )


def strategy_model(name: str | None) -> str:
    """The model a strategy file names: a file without one is refused before anything is created (R2.5.2)."""
    if name is None or not name.strip():
        raise StrategyModelMissingError
    return name
