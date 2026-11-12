from collections.abc import Callable
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from autotrading.adapters.inbound.api.tenant_use_cases import TenantUseCases
from autotrading.application.flows.archive_flow import ArchiveFlowCommand
from autotrading.application.flows.change_allocated_capital import ChangeAllocatedCapitalCommand
from autotrading.application.flows.change_flow_status import ChangeFlowStatusCommand
from autotrading.application.flows.compare_flow_versions import CompareFlowVersionsCommand
from autotrading.application.flows.create_flow import CreateFlowCommand, SourceRequest
from autotrading.application.flows.free_capital import ReadFreeCapitalCommand
from autotrading.application.flows.get_flow_version import GetFlowVersionCommand
from autotrading.application.flows.list_capital_changes import ListCapitalChangesCommand
from autotrading.application.flows.modify_flow import ModifyFlowCommand
from autotrading.application.flows.stop_flow import StopFlowCommand
from autotrading.domain.flows.capital_change import CapitalChange
from autotrading.domain.flows.configuration_difference import ConfigurationDifference
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_command import FlowCommand
from autotrading.domain.flows.flow_configuration import FlowConfiguration
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.free_capital import FreeCapital, amount_text
from autotrading.domain.flows.risk_limits import RiskLimits
from autotrading.domain.flows.selections import SourceSelection
from autotrading.domain.flows.stop_outcome import PositionLeftOpen, StopOutcome
from autotrading.domain.tenancy.user_id import UserId


class SourceSelectionRequest(BaseModel):
    name: str
    weight: int | None = None
    parameters: dict[str, int] = Field(default_factory=dict)


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
    allocated_capital: Decimal
    bring_to_minimum: bool = False

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
            model_parameters=self.model_parameters,
            sources=tuple(SourceRequest(source.name, source.weight, source.parameters) for source in self.sources),
            instructions=self.instructions,
            cycle_minutes=self.cycle_minutes,
            bring_to_minimum=self.bring_to_minimum,
        )


class FlowModificationRequest(BaseModel):
    """Only the parts the user changes; the others keep the version in force (R1.1.3)."""

    account_id: UUID | None = None
    assets: list[str] | None = None
    cycle_minutes: int | None = None
    model: str | None = None
    model_parameters: dict[str, Decimal | str] | None = None
    sources: list[SourceSelectionRequest] | None = None
    instructions: str | None = None
    max_leverage: int | None = None
    max_margin_exposure_percent: Decimal | None = None
    max_value_exposure_percent: Decimal | None = None
    bring_to_minimum: bool | None = None

    def command(self, flow_id: UUID) -> ModifyFlowCommand:
        return ModifyFlowCommand(
            flow_id=FlowId(flow_id),
            account_id=self.account_id,
            assets=None if self.assets is None else tuple(self.assets),
            model=self.model,
            model_parameters=self.model_parameters,
            sources=None
            if self.sources is None
            else tuple(SourceRequest(source.name, source.weight, source.parameters) for source in self.sources),
            instructions=self.instructions,
            cycle_minutes=self.cycle_minutes,
            max_leverage=self.max_leverage,
            max_margin_exposure_percent=self.max_margin_exposure_percent,
            max_value_exposure_percent=self.max_value_exposure_percent,
            bring_to_minimum=self.bring_to_minimum,
        )


class ModelSelectionResponse(BaseModel):
    name: str
    # Numbers travel as strings, so no precision is lost on the way (ADR 0018).
    parameters: dict[str, str]


class SourceSelectionResponse(BaseModel):
    name: str
    weight: int
    parameters: dict[str, int]

    @classmethod
    def of(cls, source: SourceSelection) -> SourceSelectionResponse:
        return cls(name=source.name, weight=source.weight, parameters=dict(source.parameters))


class RiskLimitsResponse(BaseModel):
    max_leverage: int | None
    max_margin_exposure_percent: str | None
    max_value_exposure_percent: str | None

    @classmethod
    def of(cls, limits: RiskLimits) -> RiskLimitsResponse:
        return cls(
            max_leverage=limits.max_leverage,
            max_margin_exposure_percent=_text(limits.max_margin_exposure_percent),
            max_value_exposure_percent=_text(limits.max_value_exposure_percent),
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
    allocated_capital: str
    bring_to_minimum: bool

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
            allocated_capital=amount_text(configuration.allocated_capital),
            bring_to_minimum=configuration.bring_to_minimum,
        )


class DifferenceResponse(BaseModel):
    part: str
    before: str
    after: str

    @classmethod
    def of(cls, difference: ConfigurationDifference) -> DifferenceResponse:
        return cls(part=difference.part, before=difference.before, after=difference.after)


class FlowResponse(BaseModel):
    """A flow with the configuration version in force."""

    id: UUID
    name: str
    account_id: UUID
    status: str
    version: int
    assets: list[str]
    cycle_minutes: int
    model: ModelSelectionResponse
    sources: list[SourceSelectionResponse]
    instructions: str
    risk_limits: RiskLimitsResponse
    allocated_capital: str
    bring_to_minimum: bool

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
            allocated_capital=amount_text(configuration.allocated_capital),
            bring_to_minimum=configuration.bring_to_minimum,
        )


class FreeCapitalResponse(BaseModel):
    amount: str
    currency: str

    @classmethod
    def of(cls, capital: FreeCapital) -> FreeCapitalResponse:
        return cls(amount=amount_text(capital.amount), currency=capital.currency)


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


class CapitalChangeRequest(BaseModel):
    allocated_capital: Decimal


class CapitalChangeResponse(BaseModel):
    changed_at: datetime
    previous: str
    new: str
    user_id: str

    @classmethod
    def of(cls, change: CapitalChange) -> CapitalChangeResponse:
        return cls(
            changed_at=change.changed_at,
            previous=amount_text(change.previous),
            new=amount_text(change.new),
            user_id=change.user_id.value,
        )


def flows_router(
    use_cases_of_request: Callable[..., TenantUseCases], user_of_request: Callable[..., UserId]
) -> APIRouter:
    router = APIRouter(tags=["flussi"])

    @router.post("/flows", status_code=status.HTTP_201_CREATED)
    def create_flow(
        request: FlowCreationRequest, use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)]
    ) -> FlowResponse:
        return FlowResponse.of(use_cases.create_flow.execute(request.command()))

    @router.get("/flows")
    def list_flows(
        use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)], archived: bool = False
    ) -> list[FlowResponse]:
        return [FlowResponse.of(flow) for flow in use_cases.list_flows.execute(archived=archived)]

    @router.patch("/flows/{flow_id}")
    def modify_flow(
        flow_id: UUID,
        request: FlowModificationRequest,
        use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)],
    ) -> FlowResponse:
        return FlowResponse.of(use_cases.modify_flow.execute(request.command(flow_id)))

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

    @router.put("/flows/{flow_id}/allocated-capital")
    def change_allocated_capital(
        flow_id: UUID,
        request: CapitalChangeRequest,
        use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)],
        user_id: Annotated[UserId, Depends(user_of_request)],
    ) -> FlowResponse:
        command = ChangeAllocatedCapitalCommand(FlowId(flow_id), request.allocated_capital, user_id)
        return FlowResponse.of(use_cases.change_allocated_capital.execute(command))

    @router.get("/flows/{flow_id}/capital-changes")
    def list_capital_changes(
        flow_id: UUID, use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)]
    ) -> list[CapitalChangeResponse]:
        changes = use_cases.list_capital_changes.execute(ListCapitalChangesCommand(FlowId(flow_id)))
        return [CapitalChangeResponse.of(change) for change in changes]

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


COMMANDS = {"start": FlowCommand.START, "pause": FlowCommand.PAUSE, "resume": FlowCommand.RESUME}


def _text(value: Decimal | None) -> str | None:
    return None if value is None else str(value)
