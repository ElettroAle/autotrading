"""What the writing tools receive, translated into the commands of the use cases of the API.

A missing name, model, asset or limit arrives empty, so the domain answers with the reason, as through the API.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Literal, TypedDict
from uuid import UUID

from autotrading.application.flows.create_flow import (
    ConsecutiveLossLimitRequest,
    CreateFlowCommand,
    MemoryRequest,
    SourceRequest,
    TrailingStopRequest,
)
from autotrading.application.flows.import_flow_strategy import ImportFlowStrategyCommand
from autotrading.application.flows.modify_flow import ModifyFlowCommand
from autotrading.application.flows.ports import AdapterRequest
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.openings_resume import OpeningsResume

type ParameterValue = int | list[int]
type RemovablePart = Literal[
    "system_prompt",
    "max_margin_exposure_percent",
    "max_value_exposure_percent",
    "max_total_margin_exposure_percent",
    "max_total_value_exposure_percent",
    "max_consecutive_failures",
    "max_daily_loss_percent",
    "max_drawdown_percent",
    "default_take_profit_percent",
    "minimum_confidence",
]


@dataclass(frozen=True)
class AdapterChoice:
    """An adapter of a source: no weight takes the default, a parameter not given its default."""

    name: str
    weight: int | None = None
    parameters: dict[str, ParameterValue] = field(default_factory=dict)

    def request(self) -> AdapterRequest:
        parameters = {key: tuple(value) if isinstance(value, list) else value for key, value in self.parameters.items()}
        return AdapterRequest(self.name, self.weight, parameters)


@dataclass(frozen=True)
class SourceChoice:
    """An active source with the adapters chosen: none is refused with the reason (R4.1.1)."""

    name: str
    adapters: list[AdapterChoice] = field(default_factory=list)

    def request(self) -> SourceRequest:
        return SourceRequest(self.name, tuple(adapter.request() for adapter in self.adapters))


class _StrategyArguments(TypedDict):
    max_leverage: int | None
    max_margin_exposure_percent: Decimal | None
    max_value_exposure_percent: Decimal | None
    max_total_margin_exposure_percent: Decimal | None
    max_total_value_exposure_percent: Decimal | None
    model_parameters: dict[str, Decimal | str]
    sources: tuple[SourceRequest, ...]
    instructions: str
    cycle_minutes: int | None
    bring_to_minimum: bool
    system_prompt: str | None
    max_consecutive_failures: int | None
    max_daily_loss_percent: Decimal | None
    max_drawdown_percent: Decimal | None
    openings_resume: OpeningsResume
    default_stop_loss_percent: Decimal | None
    default_take_profit_percent: Decimal | None
    minimum_confidence: int | None
    memory: MemoryRequest
    trailing_stop: TrailingStopRequest
    consecutive_loss_limit: ConsecutiveLossLimitRequest


@dataclass(frozen=True, kw_only=True)
class FlowStrategy:
    """What a flow does, shared by a new flow and an imported strategy (R1.1.1, R2.5.2)."""

    cycle_minutes: int | None = None
    model_parameters: dict[str, Decimal | str] = field(default_factory=dict)
    sources: list[SourceChoice] = field(default_factory=list)
    instructions: str = ""
    max_leverage: int | None = None
    max_margin_exposure_percent: Decimal | None = None
    max_value_exposure_percent: Decimal | None = None
    max_total_margin_exposure_percent: Decimal | None = None
    max_total_value_exposure_percent: Decimal | None = None
    bring_to_minimum: bool = False
    system_prompt: str | None = None
    max_consecutive_failures: int | None = None
    max_daily_loss_percent: Decimal | None = None
    max_drawdown_percent: Decimal | None = None
    openings_resume: OpeningsResume = OpeningsResume.MANUAL
    default_stop_loss_percent: Decimal | None = None
    default_take_profit_percent: Decimal | None = None
    minimum_confidence: int | None = None
    memory: MemoryRequest = field(default_factory=MemoryRequest)
    trailing_stop: TrailingStopRequest = field(default_factory=TrailingStopRequest)
    consecutive_loss_limit: ConsecutiveLossLimitRequest = field(default_factory=ConsecutiveLossLimitRequest)

    def _strategy_arguments(self) -> _StrategyArguments:
        return _StrategyArguments(
            max_leverage=self.max_leverage,
            max_margin_exposure_percent=self.max_margin_exposure_percent,
            max_value_exposure_percent=self.max_value_exposure_percent,
            max_total_margin_exposure_percent=self.max_total_margin_exposure_percent,
            max_total_value_exposure_percent=self.max_total_value_exposure_percent,
            model_parameters=self.model_parameters,
            sources=tuple(source.request() for source in self.sources),
            instructions=self.instructions,
            cycle_minutes=self.cycle_minutes,
            bring_to_minimum=self.bring_to_minimum,
            system_prompt=self.system_prompt,
            max_consecutive_failures=self.max_consecutive_failures,
            max_daily_loss_percent=self.max_daily_loss_percent,
            max_drawdown_percent=self.max_drawdown_percent,
            openings_resume=self.openings_resume,
            default_stop_loss_percent=self.default_stop_loss_percent,
            default_take_profit_percent=self.default_take_profit_percent,
            minimum_confidence=self.minimum_confidence,
            memory=self.memory,
            trailing_stop=self.trailing_stop,
            consecutive_loss_limit=self.consecutive_loss_limit,
        )


@dataclass(frozen=True, kw_only=True)
class FlowCreation(FlowStrategy):
    """A new flow on an account of the tenant (R1.1.1)."""

    account_id: UUID
    allocated_capital: Decimal
    name: str = ""
    assets: list[str] = field(default_factory=list)
    model: str = ""

    def command(self) -> CreateFlowCommand:
        return CreateFlowCommand(
            name=self.name,
            account_id=self.account_id,
            assets=tuple(self.assets),
            model=self.model,
            allocated_capital=self.allocated_capital,
            **self._strategy_arguments(),
        )


@dataclass(frozen=True, kw_only=True)
class StrategyImport(FlowStrategy):
    """What a flow does, without account, capital or assets: the strategy section of a strategy file (R2.5.2)."""

    model: str | None = None

    def command(self, name: str) -> ImportFlowStrategyCommand:
        return ImportFlowStrategyCommand(name=name, model=self.model, **self._strategy_arguments())


@dataclass(frozen=True)
class FlowModification:
    """Only the parts the user changes; the others keep the version in force (R1.1.3).

    A part named in `remove` goes back to none, or to the default of the platform for the system prompt: an absent
    value cannot say it, since it keeps the version in force.
    """

    name: str | None = None
    account_id: UUID | None = None
    allocated_capital: Decimal | None = None
    assets: list[str] | None = None
    cycle_minutes: int | None = None
    model: str | None = None
    model_parameters: dict[str, Decimal | str] | None = None
    sources: list[SourceChoice] | None = None
    instructions: str | None = None
    max_leverage: int | None = None
    max_margin_exposure_percent: Decimal | None = None
    max_value_exposure_percent: Decimal | None = None
    max_total_margin_exposure_percent: Decimal | None = None
    max_total_value_exposure_percent: Decimal | None = None
    bring_to_minimum: bool | None = None
    system_prompt: str | None = None
    max_consecutive_failures: int | None = None
    max_daily_loss_percent: Decimal | None = None
    max_drawdown_percent: Decimal | None = None
    openings_resume: OpeningsResume | None = None
    default_stop_loss_percent: Decimal | None = None
    default_take_profit_percent: Decimal | None = None
    minimum_confidence: int | None = None
    memory: MemoryRequest = field(default_factory=MemoryRequest)
    trailing_stop: TrailingStopRequest = field(default_factory=TrailingStopRequest)
    consecutive_loss_limit: ConsecutiveLossLimitRequest = field(default_factory=ConsecutiveLossLimitRequest)
    remove: list[RemovablePart] = field(default_factory=list)

    def command(self, flow_id: UUID) -> ModifyFlowCommand:
        removed = set(self.remove)
        return ModifyFlowCommand(
            flow_id=FlowId(flow_id),
            name=self.name,
            account_id=self.account_id,
            allocated_capital=self.allocated_capital,
            assets=None if self.assets is None else tuple(self.assets),
            model=self.model,
            model_parameters=self.model_parameters,
            sources=None if self.sources is None else tuple(source.request() for source in self.sources),
            instructions=self.instructions,
            cycle_minutes=self.cycle_minutes,
            max_leverage=self.max_leverage,
            max_margin_exposure_percent=self.max_margin_exposure_percent,
            max_value_exposure_percent=self.max_value_exposure_percent,
            max_total_margin_exposure_percent=self.max_total_margin_exposure_percent,
            max_total_value_exposure_percent=self.max_total_value_exposure_percent,
            bring_to_minimum=self.bring_to_minimum,
            system_prompt=self.system_prompt,
            max_consecutive_failures=self.max_consecutive_failures,
            default_system_prompt="system_prompt" in removed,
            remove_max_margin_exposure="max_margin_exposure_percent" in removed,
            remove_max_value_exposure="max_value_exposure_percent" in removed,
            remove_max_total_margin_exposure="max_total_margin_exposure_percent" in removed,
            remove_max_total_value_exposure="max_total_value_exposure_percent" in removed,
            remove_max_consecutive_failures="max_consecutive_failures" in removed,
            max_daily_loss_percent=self.max_daily_loss_percent,
            max_drawdown_percent=self.max_drawdown_percent,
            openings_resume=self.openings_resume,
            remove_max_daily_loss="max_daily_loss_percent" in removed,
            remove_max_drawdown="max_drawdown_percent" in removed,
            default_stop_loss_percent=self.default_stop_loss_percent,
            default_take_profit_percent=self.default_take_profit_percent,
            remove_default_take_profit="default_take_profit_percent" in removed,
            minimum_confidence=self.minimum_confidence,
            remove_minimum_confidence="minimum_confidence" in removed,
            memory=self.memory,
            trailing_stop=self.trailing_stop,
            consecutive_loss_limit=self.consecutive_loss_limit,
        )
