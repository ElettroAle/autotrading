"""A flow and the outcome of the operations on it, as the tools give them back: the fields and texts of the API."""

from collections.abc import Mapping
from dataclasses import dataclass

from autotrading.adapters.inbound.mcp.formats import optional_amount, optional_text
from autotrading.domain.flows.cash_out import CashOutOutcome
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_memory import FlowMemory
from autotrading.domain.flows.risk_limits import RiskLimits
from autotrading.domain.flows.selections import SourceSelection
from autotrading.domain.flows.stop_outcome import PositionLeftOpen, StopOutcome
from autotrading.domain.sources.source_parameter import SourceParameterValue

type ParameterValue = int | list[int]


@dataclass(frozen=True)
class ModelView:
    name: str
    parameters: dict[str, str]


@dataclass(frozen=True)
class AdapterView:
    name: str
    weight: int
    parameters: dict[str, ParameterValue]


@dataclass(frozen=True)
class SourceView:
    name: str
    adapters: list[AdapterView]

    @classmethod
    def of(cls, source: SourceSelection) -> SourceView:
        return cls(
            name=source.name,
            adapters=[
                AdapterView(name=adapter.name, weight=adapter.weight, parameters=parameter_values(adapter.parameters))
                for adapter in source.adapters
            ],
        )


@dataclass(frozen=True)
class RiskLimitsView:
    max_leverage: int | None
    max_margin_exposure_percent: str | None
    max_value_exposure_percent: str | None
    max_total_margin_exposure_percent: str | None
    max_total_value_exposure_percent: str | None

    @classmethod
    def of(cls, limits: RiskLimits) -> RiskLimitsView:
        return cls(
            max_leverage=limits.max_leverage,
            max_margin_exposure_percent=optional_text(limits.max_margin_exposure_percent),
            max_value_exposure_percent=optional_text(limits.max_value_exposure_percent),
            max_total_margin_exposure_percent=optional_text(limits.max_total_margin_exposure_percent),
            max_total_value_exposure_percent=optional_text(limits.max_total_value_exposure_percent),
        )


@dataclass(frozen=True)
class MemoryView:
    active: bool
    decisions: int
    days: int

    @classmethod
    def of(cls, memory: FlowMemory) -> MemoryView:
        return cls(active=memory.active, decisions=memory.decisions, days=memory.days)


@dataclass(frozen=True)
class FlowView:
    """A flow with the configuration version in force; a draft may have no account, capital or assets (ADR 0124)."""

    id: str
    name: str
    account_id: str | None
    status: str
    version: int
    assets: list[str]
    cycle_minutes: int
    model: ModelView
    sources: list[SourceView]
    instructions: str
    risk_limits: RiskLimitsView
    allocated_capital: str | None
    bring_to_minimum: bool
    system_prompt: str
    system_prompt_is_default: bool
    max_consecutive_failures: int | None
    max_daily_loss_percent: str | None
    max_drawdown_percent: str | None
    openings_resume: str
    default_stop_loss_percent: str
    default_take_profit_percent: str | None
    minimum_confidence: int | None
    memory: MemoryView
    missing: list[str]

    @classmethod
    def of(cls, flow: Flow) -> FlowView:
        configuration = flow.configuration
        model = configuration.model
        confidence = configuration.minimum_confidence
        return cls(
            id=str(flow.id.value),
            name=flow.name.value,
            account_id=None if flow.account_id is None else str(flow.account_id),
            status=flow.status.value,
            version=configuration.version,
            assets=list(configuration.assets),
            cycle_minutes=configuration.cycle_interval.minutes,
            model=ModelView(name=model.name, parameters={key: str(value) for key, value in model.parameters.items()}),
            sources=[SourceView.of(source) for source in configuration.sources],
            instructions=configuration.instructions,
            risk_limits=RiskLimitsView.of(configuration.risk_limits),
            allocated_capital=optional_amount(configuration.allocated_capital),
            bring_to_minimum=configuration.bring_to_minimum,
            system_prompt=configuration.system_prompt_template,
            system_prompt_is_default=configuration.system_prompt is None,
            max_consecutive_failures=configuration.max_consecutive_failures,
            max_daily_loss_percent=optional_text(configuration.max_daily_loss_percent),
            max_drawdown_percent=optional_text(configuration.max_drawdown_percent),
            openings_resume=configuration.openings_resume.value,
            default_stop_loss_percent=str(configuration.protection_defaults.stop_loss_percent),
            default_take_profit_percent=optional_text(configuration.protection_defaults.take_profit_percent),
            minimum_confidence=None if confidence is None else confidence.value,
            memory=MemoryView.of(configuration.memory),
            missing=list(flow.missing_before_start),
        )


@dataclass(frozen=True)
class PositionLeftOpenView:
    asset: str
    reason: str

    @classmethod
    def of(cls, position: PositionLeftOpen) -> PositionLeftOpenView:
        return cls(asset=position.asset, reason=position.reason)


@dataclass(frozen=True)
class StopOutcomeView:
    """The flow stopped and the positions the exchange did not close, each with its reason (R1.1.5)."""

    flow: FlowView
    left_open: list[PositionLeftOpenView]

    @classmethod
    def of(cls, outcome: StopOutcome) -> StopOutcomeView:
        return cls(
            flow=FlowView.of(outcome.flow), left_open=[PositionLeftOpenView.of(each) for each in outcome.left_open]
        )


@dataclass(frozen=True)
class CashOutView:
    """The flow after the cash-out, the money it freed and the positions not closed (R3.4.1)."""

    flow: FlowView
    freed: str | None
    capital: str | None
    left_open: list[PositionLeftOpenView]

    @classmethod
    def of(cls, outcome: CashOutOutcome) -> CashOutView:
        return cls(
            flow=FlowView.of(outcome.flow),
            freed=optional_amount(outcome.freed),
            capital=optional_amount(outcome.flow.configuration.allocated_capital),
            left_open=[PositionLeftOpenView.of(each) for each in outcome.left_open],
        )


@dataclass(frozen=True)
class OpeningsResumedView:
    """The openings of the flow resumed after a maximum loss (R3.2.2)."""

    flow_id: str


def parameter_values(parameters: Mapping[str, SourceParameterValue]) -> dict[str, ParameterValue]:
    return {key: list(value) if isinstance(value, tuple) else value for key, value in parameters.items()}
