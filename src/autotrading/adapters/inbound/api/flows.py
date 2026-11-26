from collections.abc import Callable
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from autotrading.adapters.inbound.api.amounts import amount_text
from autotrading.adapters.inbound.api.cycles import CycleSummaryResponse
from autotrading.adapters.inbound.api.source_parameters import ParameterBody, parameters_body, parameters_of
from autotrading.adapters.inbound.api.strategy_document import StrategyDocument, attachment_of
from autotrading.adapters.inbound.api.tenant_use_cases import TenantUseCases
from autotrading.application.flows.archive_flow import ArchiveFlowCommand
from autotrading.application.flows.cash_out_profits import CashOutProfitsCommand
from autotrading.application.flows.change_allocated_capital import ChangeAllocatedCapitalCommand
from autotrading.application.flows.change_flow_status import ChangeFlowStatusCommand
from autotrading.application.flows.compare_flow_versions import CompareFlowVersionsCommand
from autotrading.application.flows.create_flow import (
    ConsecutiveLossLimitRequest,
    CreateFlowCommand,
    MemoryRequest,
    SourceRequest,
    TrailingStopRequest,
)
from autotrading.application.flows.duplicate_flow import DuplicateFlowCommand
from autotrading.application.flows.export_flow_strategy import ExportFlowStrategyCommand
from autotrading.application.flows.get_flow import GetFlowCommand
from autotrading.application.flows.get_flow_version import GetFlowVersionCommand
from autotrading.application.flows.list_flow_versions import ListFlowVersionsCommand
from autotrading.application.flows.modify_flow import ModifyFlowCommand
from autotrading.application.flows.ports import AdapterRequest, FlowVersion
from autotrading.application.flows.read_default_system_prompt import DefaultSystemPrompt
from autotrading.application.flows.read_flow_memory import FlowMemoryReading, ReadFlowMemoryCommand
from autotrading.application.flows.read_free_capital import ReadFreeCapitalCommand
from autotrading.application.flows.request_on_demand_cycle import RequestOnDemandCycleCommand
from autotrading.application.flows.resume_flow_openings import ResumeFlowOpeningsCommand
from autotrading.application.flows.stop_flow import StopFlowCommand
from autotrading.domain.flows.cash_out import CashOutOutcome
from autotrading.domain.flows.configuration_difference import ConfigurationDifference
from autotrading.domain.flows.consecutive_loss_limit import ConsecutiveLossLimit, LossCountScope
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_action import FlowAction
from autotrading.domain.flows.flow_configuration import FlowConfiguration
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.flow_memory import FlowMemory
from autotrading.domain.flows.free_capital import FreeCapital
from autotrading.domain.flows.minimum_confidence import MinimumConfidence
from autotrading.domain.flows.openings_resume import OpeningsResume
from autotrading.domain.flows.risk_limits import RiskLimits
from autotrading.domain.flows.selections import SourceSelection
from autotrading.domain.flows.stop_outcome import PositionLeftOpen, StopOutcome
from autotrading.domain.flows.system_prompt import PromptPlaceholder
from autotrading.domain.flows.trailing_stop import TrailingStop
from autotrading.domain.tenancy.user_id import UserId


class AdapterSelectionRequest(BaseModel):
    name: str
    weight: int | None = None
    parameters: dict[str, ParameterBody] = Field(default_factory=dict)

    def request(self) -> AdapterRequest:
        return AdapterRequest(self.name, self.weight, parameters_of(self.parameters))


class SourceSelectionRequest(BaseModel):
    """An active source with the adapters chosen: none is refused with the reason (R4.1.1)."""

    name: str
    adapters: list[AdapterSelectionRequest] = Field(default_factory=list)

    def request(self) -> SourceRequest:
        return SourceRequest(self.name, tuple(adapter.request() for adapter in self.adapters))


class FlowCreationRequest(BaseModel):
    """A missing name, model, asset or risk limit arrives empty, so the domain answers with the reason (R1.1.1)."""

    name: str = ""
    account_id: UUID
    assets: list[str] = Field(default_factory=list)
    cycle_minutes: int | None = None
    model: str = ""
    model_parameters: dict[str, Decimal | str] = Field(default_factory=dict)
    sources: list[SourceSelectionRequest] = Field(default_factory=list)
    instructions: str = ""
    max_leverage: int | None = None
    max_margin_exposure_percent: Decimal | None = None
    max_value_exposure_percent: Decimal | None = None
    # Null or missing: no overall limit on the sum of the open positions (R3.2.1).
    max_total_margin_exposure_percent: Decimal | None = None
    max_total_value_exposure_percent: Decimal | None = None
    allocated_capital: Decimal
    bring_to_minimum: bool = False
    # Null or missing follows the default of the platform (R1.4.8).
    system_prompt: str | None = None
    # Null or missing: no maximum, the flow keeps trying at every cycle (R3.2.4).
    max_consecutive_failures: int | None = None
    # Null or missing: no maximum loss; the suspended openings resume by hand unless "next_day" (R3.2.2).
    max_daily_loss_percent: Decimal | None = None
    max_drawdown_percent: Decimal | None = None
    openings_resume: OpeningsResume = OpeningsResume.MANUAL
    # Null or missing: a stop loss of 5% and no take profit (R3.1.2).
    default_stop_loss_percent: Decimal | None = None
    default_take_profit_percent: Decimal | None = None
    # Null or missing: no minimum confidence (R3.1.4).
    minimum_confidence: int | None = None
    # Missing: off, with 10 decisions and 30 days (R5.3.4), a motive of 160 characters and only openings, closings and
    # reversals; `unlimited_text_length` true leaves the motive whole (R5.3.5); summary and other assets off (R5.3.7).
    memory: MemoryRequest = Field(default_factory=MemoryRequest)
    # Missing: no stop that follows the price, the option of the agent off (R5.5.1).
    trailing_stop: TrailingStopRequest = Field(default_factory=TrailingStopRequest)
    # Missing: no block of the openings after consecutive losses; the three numbers go together, the scope «asset» or
    # «flusso», the asset if not given (R5.5.2).
    consecutive_loss_limit: ConsecutiveLossLimitRequest = Field(default_factory=ConsecutiveLossLimitRequest)
    # Missing: the agent sees the flow alone, never the other flows of its account (R5.5.5).
    account_exposure_for_agent: bool = False
    # Missing: the agent does not see the cost of opening and closing a position (R5.5.6).
    fees_for_agent: bool = False

    def command(self) -> CreateFlowCommand:
        return CreateFlowCommand(
            name=self.name,
            account_id=self.account_id,
            assets=tuple(self.assets),
            model=self.model,
            allocated_capital=self.allocated_capital,
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
            account_exposure_for_agent=self.account_exposure_for_agent,
            fees_for_agent=self.fees_for_agent,
        )


class FlowModificationRequest(BaseModel):
    """Only the parts the user changes; the others keep the version in force (R1.1.3).

    Account and allocated capital are taken by a draft (ADR bozza-configurata-dall-editor-e-duplica-con-conto); the
    name by every flow not archived (ADR nome-del-flusso-modificabile).
    """

    name: str | None = None
    account_id: UUID | None = None
    allocated_capital: Decimal | None = None
    assets: list[str] | None = None
    cycle_minutes: int | None = None
    model: str | None = None
    model_parameters: dict[str, Decimal | str] | None = None
    sources: list[SourceSelectionRequest] | None = None
    instructions: str | None = None
    max_leverage: int | None = None
    # A null sent on purpose removes the limit; a missing one keeps the version in force (R1.1.3).
    max_margin_exposure_percent: Decimal | None = None
    max_value_exposure_percent: Decimal | None = None
    max_total_margin_exposure_percent: Decimal | None = None
    max_total_value_exposure_percent: Decimal | None = None
    bring_to_minimum: bool | None = None
    # A null sent on purpose goes back to the default; a missing one keeps the version in force (R1.4.8).
    system_prompt: str | None = None
    max_consecutive_failures: int | None = None
    # A null sent on purpose removes the maximum loss; a missing one keeps the version in force (R3.2.2).
    max_daily_loss_percent: Decimal | None = None
    max_drawdown_percent: Decimal | None = None
    openings_resume: OpeningsResume | None = None
    default_stop_loss_percent: Decimal | None = None
    # A null sent on purpose removes the default take profit; a missing one keeps the version in force (R3.1.2).
    default_take_profit_percent: Decimal | None = None
    # A null sent on purpose removes the minimum confidence; a missing one keeps the version in force (R3.1.4).
    minimum_confidence: int | None = None
    # Only the parts of the memory sent change; the others keep the version in force (R5.3.4). A null length keeps it
    # too: `unlimited_text_length` true takes the limit away (R5.3.5).
    memory: MemoryRequest = Field(default_factory=MemoryRequest)
    # Only the parts of the stop that follows the price sent change; `remove_*` takes a part away (R5.5.1).
    trailing_stop: TrailingStopRequest = Field(default_factory=TrailingStopRequest)
    # Missing keeps the limit of consecutive losses; sent, it replaces it whole; `remove_limit` takes it away (R5.5.2).
    consecutive_loss_limit: ConsecutiveLossLimitRequest = Field(default_factory=ConsecutiveLossLimitRequest)
    # Missing keeps the option in force (R5.5.5).
    account_exposure_for_agent: bool | None = None
    # Missing keeps the option in force (R5.5.6).
    fees_for_agent: bool | None = None

    def command(self, flow_id: UUID) -> ModifyFlowCommand:
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
            default_system_prompt=self._sent_as_null("system_prompt"),
            remove_max_margin_exposure=self._sent_as_null("max_margin_exposure_percent"),
            remove_max_value_exposure=self._sent_as_null("max_value_exposure_percent"),
            remove_max_total_margin_exposure=self._sent_as_null("max_total_margin_exposure_percent"),
            remove_max_total_value_exposure=self._sent_as_null("max_total_value_exposure_percent"),
            remove_max_consecutive_failures=self._sent_as_null("max_consecutive_failures"),
            max_daily_loss_percent=self.max_daily_loss_percent,
            max_drawdown_percent=self.max_drawdown_percent,
            openings_resume=self.openings_resume,
            remove_max_daily_loss=self._sent_as_null("max_daily_loss_percent"),
            remove_max_drawdown=self._sent_as_null("max_drawdown_percent"),
            default_stop_loss_percent=self.default_stop_loss_percent,
            default_take_profit_percent=self.default_take_profit_percent,
            remove_default_take_profit=self._sent_as_null("default_take_profit_percent"),
            minimum_confidence=self.minimum_confidence,
            remove_minimum_confidence=self._sent_as_null("minimum_confidence"),
            memory=self.memory,
            trailing_stop=self.trailing_stop,
            consecutive_loss_limit=self.consecutive_loss_limit,
            account_exposure_for_agent=self.account_exposure_for_agent,
            fees_for_agent=self.fees_for_agent,
        )

    def _sent_as_null(self, field: str) -> bool:
        return field in self.model_fields_set and getattr(self, field) is None


class ModelSelectionResponse(BaseModel):
    name: str
    # Numbers travel as strings, so no precision is lost on the way (ADR 0018).
    parameters: dict[str, str]


class AdapterSelectionResponse(BaseModel):
    name: str
    weight: int
    parameters: dict[str, ParameterBody]


class SourceSelectionResponse(BaseModel):
    name: str
    adapters: list[AdapterSelectionResponse]

    @classmethod
    def of(cls, source: SourceSelection) -> SourceSelectionResponse:
        return cls(
            name=source.name,
            adapters=[
                AdapterSelectionResponse(
                    name=adapter.name, weight=adapter.weight, parameters=parameters_body(adapter.parameters)
                )
                for adapter in source.adapters
            ],
        )


class RiskLimitsResponse(BaseModel):
    max_leverage: int | None
    max_margin_exposure_percent: str | None
    max_value_exposure_percent: str | None
    max_total_margin_exposure_percent: str | None
    max_total_value_exposure_percent: str | None

    @classmethod
    def of(cls, limits: RiskLimits) -> RiskLimitsResponse:
        return cls(
            max_leverage=limits.max_leverage,
            max_margin_exposure_percent=_text(limits.max_margin_exposure_percent),
            max_value_exposure_percent=_text(limits.max_value_exposure_percent),
            max_total_margin_exposure_percent=_text(limits.max_total_margin_exposure_percent),
            max_total_value_exposure_percent=_text(limits.max_total_value_exposure_percent),
        )


class TrailingStopResponse(BaseModel):
    """The stop that follows the price of a version, every part present, null when empty (R5.5.1)."""

    distance_percent: str | None
    activation_percent: str | None
    breakeven_percent: str | None
    max_profit_in_context: bool

    @classmethod
    def of(cls, trailing: TrailingStop) -> TrailingStopResponse:
        return cls(
            distance_percent=_text(trailing.distance_percent),
            activation_percent=_text(trailing.activation_percent),
            breakeven_percent=_text(trailing.breakeven_percent),
            max_profit_in_context=trailing.max_profit_in_context,
        )


class ConsecutiveLossLimitResponse(BaseModel):
    """The limit of consecutive losses of a version (R5.5.2)."""

    max_consecutive_losses: int
    loss_window_hours: int
    block_minutes: int
    count_scope: LossCountScope

    @classmethod
    def of(cls, limit: ConsecutiveLossLimit | None) -> ConsecutiveLossLimitResponse | None:
        if limit is None:
            return None
        return cls(
            max_consecutive_losses=limit.max_consecutive_losses,
            loss_window_hours=limit.loss_window_hours,
            block_minutes=limit.block_minutes,
            count_scope=limit.count_scope,
        )


class PromptPlaceholderResponse(BaseModel):
    """A placeholder the system prompt may use, with what it stands for (R1.4.8)."""

    name: str
    description: str

    @classmethod
    def all(cls) -> list[PromptPlaceholderResponse]:
        return [cls(name=placeholder.value, description=placeholder.description) for placeholder in PromptPlaceholder]


class DefaultSystemPromptResponse(BaseModel):
    """The system prompt a new flow starts with, and the placeholders it may use (R1.4.8)."""

    system_prompt: str
    system_prompt_placeholders: list[PromptPlaceholderResponse]

    @classmethod
    def of(cls, default: DefaultSystemPrompt) -> DefaultSystemPromptResponse:
        return cls(
            system_prompt=default.template,
            system_prompt_placeholders=[
                PromptPlaceholderResponse(name=placeholder.value, description=placeholder.description)
                for placeholder in default.placeholders
            ],
        )


class ConfigurationResponse(BaseModel):
    """One configuration version of a flow."""

    version: int
    assets: list[str]
    cycle_minutes: int
    model: ModelSelectionResponse
    sources: list[SourceSelectionResponse]
    instructions: str
    risk_limits: RiskLimitsResponse
    # None only in the versions of a draft (ADR 0124).
    allocated_capital: str | None
    bring_to_minimum: bool
    system_prompt: str
    system_prompt_is_default: bool
    system_prompt_placeholders: list[PromptPlaceholderResponse]
    # None: no maximum of failed cycles in a row (R3.2.4).
    max_consecutive_failures: int | None
    # None: no maximum loss (R3.2.2).
    max_daily_loss_percent: str | None
    max_drawdown_percent: str | None
    openings_resume: OpeningsResume
    default_stop_loss_percent: str
    default_take_profit_percent: str | None
    minimum_confidence: int | None
    memory: FlowMemory
    trailing_stop: TrailingStopResponse
    # Null for a flow without the limit (R5.5.2).
    consecutive_loss_limit: ConsecutiveLossLimitResponse | None
    account_exposure_for_agent: bool
    fees_for_agent: bool

    @classmethod
    def of(cls, configuration: FlowConfiguration) -> ConfigurationResponse:
        model = configuration.model
        return cls(
            version=configuration.version,
            assets=list(configuration.assets),
            cycle_minutes=configuration.cycle_interval.minutes,
            model=ModelSelectionResponse(
                name=model.name, parameters={key: str(value) for key, value in model.parameters.items()}
            ),
            sources=[SourceSelectionResponse.of(source) for source in configuration.sources],
            instructions=configuration.instructions,
            risk_limits=RiskLimitsResponse.of(configuration.risk_limits),
            allocated_capital=_amount(configuration.allocated_capital),
            bring_to_minimum=configuration.bring_to_minimum,
            system_prompt=configuration.system_prompt_template,
            system_prompt_is_default=configuration.system_prompt is None,
            system_prompt_placeholders=PromptPlaceholderResponse.all(),
            max_consecutive_failures=configuration.max_consecutive_failures,
            max_daily_loss_percent=_text(configuration.max_daily_loss_percent),
            max_drawdown_percent=_text(configuration.max_drawdown_percent),
            openings_resume=configuration.openings_resume,
            default_stop_loss_percent=str(configuration.protection_defaults.stop_loss_percent),
            default_take_profit_percent=_text(configuration.protection_defaults.take_profit_percent),
            minimum_confidence=_confidence(configuration.minimum_confidence),
            memory=configuration.memory,
            trailing_stop=TrailingStopResponse.of(configuration.trailing_stop),
            consecutive_loss_limit=ConsecutiveLossLimitResponse.of(configuration.consecutive_loss_limit),
            account_exposure_for_agent=configuration.account_exposure_for_agent,
            fees_for_agent=configuration.fees_for_agent,
        )


class VersionResponse(BaseModel):
    """One configuration version of a flow in the list: its number and when it was saved (R2.3.5)."""

    version: int
    created_at: datetime

    @classmethod
    def of(cls, version: FlowVersion) -> VersionResponse:
        return cls(version=version.number, created_at=version.created_at)


class DifferenceResponse(BaseModel):
    part: str
    before: str
    after: str

    @classmethod
    def of(cls, difference: ConfigurationDifference) -> DifferenceResponse:
        return cls(part=difference.part, before=difference.before, after=difference.after)


class FlowResponse(BaseModel):
    """A flow with the configuration version in force; a draft may have no account, capital or assets (ADR 0124)."""

    id: UUID
    name: str
    account_id: UUID | None
    status: str
    version: int
    assets: list[str]
    cycle_minutes: int
    model: ModelSelectionResponse
    sources: list[SourceSelectionResponse]
    instructions: str
    risk_limits: RiskLimitsResponse
    allocated_capital: str | None
    bring_to_minimum: bool
    system_prompt: str
    system_prompt_is_default: bool
    system_prompt_placeholders: list[PromptPlaceholderResponse]
    max_consecutive_failures: int | None
    max_daily_loss_percent: str | None
    max_drawdown_percent: str | None
    openings_resume: OpeningsResume
    default_stop_loss_percent: str
    default_take_profit_percent: str | None
    minimum_confidence: int | None
    memory: FlowMemory
    trailing_stop: TrailingStopResponse
    # Null for a flow without the limit (R5.5.2).
    consecutive_loss_limit: ConsecutiveLossLimitResponse | None
    account_exposure_for_agent: bool
    fees_for_agent: bool
    missing: list[str]

    @classmethod
    def of(cls, flow: Flow) -> FlowResponse:
        configuration = flow.configuration
        model = configuration.model
        return cls(
            id=flow.id.value,
            name=flow.name.value,
            account_id=flow.account_id,
            status=flow.status.value,
            version=configuration.version,
            assets=list(configuration.assets),
            cycle_minutes=configuration.cycle_interval.minutes,
            model=ModelSelectionResponse(
                name=model.name, parameters={key: str(value) for key, value in model.parameters.items()}
            ),
            sources=[SourceSelectionResponse.of(source) for source in configuration.sources],
            instructions=configuration.instructions,
            risk_limits=RiskLimitsResponse.of(configuration.risk_limits),
            allocated_capital=_amount(configuration.allocated_capital),
            bring_to_minimum=configuration.bring_to_minimum,
            system_prompt=configuration.system_prompt_template,
            system_prompt_is_default=configuration.system_prompt is None,
            system_prompt_placeholders=PromptPlaceholderResponse.all(),
            max_consecutive_failures=configuration.max_consecutive_failures,
            max_daily_loss_percent=_text(configuration.max_daily_loss_percent),
            max_drawdown_percent=_text(configuration.max_drawdown_percent),
            openings_resume=configuration.openings_resume,
            default_stop_loss_percent=str(configuration.protection_defaults.stop_loss_percent),
            default_take_profit_percent=_text(configuration.protection_defaults.take_profit_percent),
            minimum_confidence=_confidence(configuration.minimum_confidence),
            memory=configuration.memory,
            trailing_stop=TrailingStopResponse.of(configuration.trailing_stop),
            consecutive_loss_limit=ConsecutiveLossLimitResponse.of(configuration.consecutive_loss_limit),
            account_exposure_for_agent=configuration.account_exposure_for_agent,
            fees_for_agent=configuration.fees_for_agent,
            missing=list(flow.missing_before_start),
        )


class FreeCapitalResponse(BaseModel):
    """The free capital of the account with the value and the result of its flows: the balance is the value of the flows
    plus the free capital (ADR scomposizione-del-saldo-nel-riquadro-del-conto).
    """

    amount: str
    currency: str
    flows_value: str
    flows_result: str

    @classmethod
    def of(cls, capital: FreeCapital) -> FreeCapitalResponse:
        return cls(
            amount=amount_text(capital.amount),
            currency=capital.currency,
            flows_value=amount_text(capital.flows_value),
            flows_result=amount_text(capital.flows_result),
        )


class PositionLeftOpenResponse(BaseModel):
    asset: str
    reason: str

    @classmethod
    def of(cls, position: PositionLeftOpen) -> PositionLeftOpenResponse:
        return cls(asset=position.asset, reason=position.reason)


class StopOutcomeResponse(BaseModel):
    """The flow stopped and the positions the exchange did not close, each with its reason (R1.1.5)."""

    flow: FlowResponse
    left_open: list[PositionLeftOpenResponse]

    @classmethod
    def of(cls, outcome: StopOutcome) -> StopOutcomeResponse:
        return cls(
            flow=FlowResponse.of(outcome.flow),
            left_open=[PositionLeftOpenResponse.of(position) for position in outcome.left_open],
        )


class CashOutRequest(BaseModel):
    """The capital the flow keeps after the cash-out; without it, the capital allocated now (R3.4.1)."""

    capital: Decimal | None = None


class CashOutOutcomeResponse(BaseModel):
    """The flow after the cash-out, the money it freed and the positions not closed, each with its reason (R3.4.1).

    With a position left open nothing is freed.
    """

    flow: FlowResponse
    freed: str | None
    capital: str | None
    left_open: list[PositionLeftOpenResponse]

    @classmethod
    def of(cls, outcome: CashOutOutcome) -> CashOutOutcomeResponse:
        return cls(
            flow=FlowResponse.of(outcome.flow),
            freed=_amount(outcome.freed),
            capital=_amount(outcome.flow.configuration.allocated_capital),
            left_open=[PositionLeftOpenResponse.of(position) for position in outcome.left_open],
        )


class CapitalChangeRequest(BaseModel):
    allocated_capital: Decimal


def flows_router(
    use_cases_of_request: Callable[..., TenantUseCases], user_of_request: Callable[..., UserId]
) -> APIRouter:
    router = APIRouter(tags=["flussi"])

    @router.post("/flows", status_code=status.HTTP_201_CREATED)
    def create_flow(
        request: FlowCreationRequest, use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)]
    ) -> FlowResponse:
        return FlowResponse.of(use_cases.create_flow.execute(request.command()))

    @router.post("/flows/import", status_code=status.HTTP_201_CREATED)
    def import_flow_strategy(
        document: StrategyDocument,
        use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)],
        name: str = "",
    ) -> FlowResponse:
        """A draft named as asked, with the strategy of the file sent as it is (R2.5.2, ADR 0140)."""
        return FlowResponse.of(use_cases.import_flow_strategy.execute(document.command(name)))

    @router.get("/flows/system-prompt")
    def read_default_system_prompt(
        use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)],
    ) -> DefaultSystemPromptResponse:
        return DefaultSystemPromptResponse.of(use_cases.read_default_system_prompt.execute())

    @router.get("/flows")
    def list_flows(
        use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)], archived: bool = False
    ) -> list[FlowResponse]:
        return [FlowResponse.of(flow) for flow in use_cases.list_flows.execute(archived=archived)]

    @router.get("/flows/{flow_id}")
    def get_flow(flow_id: UUID, use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)]) -> FlowResponse:
        """One flow of the tenant, an archived one too, which the list leaves out (Bug 690)."""
        return FlowResponse.of(use_cases.get_flow.execute(GetFlowCommand(FlowId(flow_id))))

    @router.patch("/flows/{flow_id}")
    def modify_flow(
        flow_id: UUID,
        request: FlowModificationRequest,
        use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)],
    ) -> FlowResponse:
        return FlowResponse.of(use_cases.modify_flow.execute(request.command(flow_id)))

    @router.get("/flows/{flow_id}/versions")
    def list_flow_versions(
        flow_id: UUID, use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)]
    ) -> list[VersionResponse]:
        command = ListFlowVersionsCommand(FlowId(flow_id))
        return [VersionResponse.of(version) for version in use_cases.list_flow_versions.execute(command)]

    @router.get("/flows/{flow_id}/versions/{version}")
    def get_flow_version(
        flow_id: UUID, version: int, use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)]
    ) -> ConfigurationResponse:
        command = GetFlowVersionCommand(FlowId(flow_id), version)
        return ConfigurationResponse.of(use_cases.get_flow_version.execute(command))

    @router.get("/flows/{flow_id}/versions/{first}/differences/{second}")
    def compare_flow_versions(
        flow_id: UUID, first: int, second: int, use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)]
    ) -> list[DifferenceResponse]:
        command = CompareFlowVersionsCommand(FlowId(flow_id), first, second)
        return [DifferenceResponse.of(difference) for difference in use_cases.compare_flow_versions.execute(command)]

    @router.get("/flows/{flow_id}/memory")
    def read_flow_memory(
        flow_id: UUID, use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)]
    ) -> FlowMemoryReading:
        """The memory the agent of the flow would receive if its cycle started now (R5.3.4)."""
        return use_cases.read_flow_memory.execute(ReadFlowMemoryCommand(FlowId(flow_id)))

    @router.post("/flows/{flow_id}/archive")
    def archive_flow(
        flow_id: UUID, use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)]
    ) -> FlowResponse:
        return FlowResponse.of(use_cases.archive_flow.execute(ArchiveFlowCommand(FlowId(flow_id))))

    @router.post("/flows/{flow_id}/stop")
    def stop_flow(
        flow_id: UUID,
        use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)],
        user_id: Annotated[UserId, Depends(user_of_request)],
    ) -> StopOutcomeResponse:
        return StopOutcomeResponse.of(use_cases.stop_flow.execute(StopFlowCommand(FlowId(flow_id), user_id)))

    @router.post("/flows/{flow_id}/cash-out")
    def cash_out_profits(
        flow_id: UUID,
        use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)],
        user_id: Annotated[UserId, Depends(user_of_request)],
        request: CashOutRequest | None = None,
    ) -> CashOutOutcomeResponse:
        capital = None if request is None else request.capital
        command = CashOutProfitsCommand(FlowId(flow_id), user_id, capital)
        return CashOutOutcomeResponse.of(use_cases.cash_out_profits.execute(command))

    @router.put("/flows/{flow_id}/allocated-capital")
    def change_allocated_capital(
        flow_id: UUID,
        request: CapitalChangeRequest,
        use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)],
        user_id: Annotated[UserId, Depends(user_of_request)],
    ) -> FlowResponse:
        command = ChangeAllocatedCapitalCommand(FlowId(flow_id), request.allocated_capital, user_id)
        return FlowResponse.of(use_cases.change_allocated_capital.execute(command))

    # Before the commands of the status, whose path would take "cycles" for an action.
    @router.post("/flows/{flow_id}/cycles", status_code=status.HTTP_201_CREATED)
    def run_cycle_now(
        flow_id: UUID, use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)]
    ) -> CycleSummaryResponse:
        """A cycle of the flow now, run by the worker and answered when it ends (R6.5.2): a failed cycle is the
        cycle created, a flow not active or a cycle in progress a refusal."""
        command = RequestOnDemandCycleCommand(flow_id)
        return CycleSummaryResponse.of(use_cases.request_on_demand_cycle.execute(command))

    @router.post("/flows/{flow_id}/duplicate", status_code=status.HTTP_201_CREATED)
    def duplicate_flow(
        flow_id: UUID, use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)]
    ) -> FlowResponse:
        return FlowResponse.of(use_cases.duplicate_flow.execute(DuplicateFlowCommand(FlowId(flow_id))))

    @router.get("/flows/{flow_id}/strategy", response_model=StrategyDocument)
    def export_flow_strategy(
        flow_id: UUID, use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)]
    ) -> JSONResponse:
        """The strategy file of the flow, to download under the name of the flow (R2.5.2, ADR 0140)."""
        exported = use_cases.export_flow_strategy.execute(ExportFlowStrategyCommand(FlowId(flow_id)))
        return JSONResponse(
            StrategyDocument.of(exported.strategy).model_dump(mode="json"),
            headers={"Content-Disposition": attachment_of(exported.flow_name.value)},
        )

    @router.post("/flows/{flow_id}/openings/resume", status_code=204)
    def resume_flow_openings(
        flow_id: UUID, use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)]
    ) -> None:
        """The user resumes the openings suspended for maximum loss (R3.2.2); the suspension in force, of any cause,
        reads in the state of the flow.
        """
        use_cases.resume_flow_openings.execute(ResumeFlowOpeningsCommand(FlowId(flow_id)))

    @router.post("/flows/{flow_id}/{action}")
    def change_flow_status(
        flow_id: UUID,
        action: Literal["start", "pause", "resume"],
        use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)],
    ) -> FlowResponse:
        command = ChangeFlowStatusCommand(FlowId(flow_id), COMMANDS[action])
        return FlowResponse.of(use_cases.change_flow_status.execute(command))

    @router.get("/accounts/{account_id}/free-capital")
    def read_free_capital(
        account_id: UUID, use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)]
    ) -> FreeCapitalResponse:
        return FreeCapitalResponse.of(use_cases.read_free_capital.execute(ReadFreeCapitalCommand(account_id)))

    return router


COMMANDS = {"start": FlowAction.START, "pause": FlowAction.PAUSE, "resume": FlowAction.RESUME}


def _amount(value: Decimal | None) -> str | None:
    return None if value is None else amount_text(value)


def _confidence(minimum: MinimumConfidence | None) -> int | None:
    return None if minimum is None else minimum.value


def _text(value: Decimal | None) -> str | None:
    return None if value is None else str(value)
