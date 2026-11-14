from dataclasses import dataclass

from autotrading.domain.flows.cycle_interval import CycleInterval
from autotrading.domain.flows.errors import StrategyModelMissingError
from autotrading.domain.flows.flow_configuration import FlowConfiguration
from autotrading.domain.flows.risk_limits import RiskLimits
from autotrading.domain.flows.selections import ModelSelection, SourceSelection


@dataclass(frozen=True, slots=True)
class FlowStrategy:
    """What a flow does, without where and with how much: the part of a configuration a strategy file carries.

    Interval, sources with weights and parameters, model with its parameters, instructions and risk rules; account,
    allocated capital and assets belong to the flow that uses the strategy, assigned to its draft (R2.5.2, ADR 0140).
    """

    cycle_interval: CycleInterval
    model: ModelSelection
    sources: tuple[SourceSelection, ...]
    instructions: str
    risk_limits: RiskLimits
    # Off unless the user chooses it, as in the configuration: a risk rule like the limits (R1.5.4).
    bring_to_minimum: bool = False

    @classmethod
    def of(cls, configuration: FlowConfiguration) -> FlowStrategy:
        return cls(
            configuration.cycle_interval,
            configuration.model,
            configuration.sources,
            configuration.instructions,
            configuration.risk_limits,
            configuration.bring_to_minimum,
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
        )


def strategy_model(name: str | None) -> str:
    """The model a strategy file names: a file without one is refused before anything is created (R2.5.2)."""
    if name is None or not name.strip():
        raise StrategyModelMissingError
    return name
