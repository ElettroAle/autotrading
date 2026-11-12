from collections.abc import Callable
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from autotrading.adapters.inbound.api.tenant_use_cases import TenantUseCases
from autotrading.application.flows.create_flow import CreateFlowCommand, SourceRequest
from autotrading.application.flows.free_capital import ReadFreeCapitalCommand
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.free_capital import FreeCapital, amount_text
from autotrading.domain.flows.risk_limits import RiskLimits
from autotrading.domain.flows.selections import SourceSelection


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
        )


class FreeCapitalResponse(BaseModel):
    amount: str
    currency: str

    @classmethod
    def of(cls, capital: FreeCapital) -> FreeCapitalResponse:
        return cls(amount=amount_text(capital.amount), currency=capital.currency)


def flows_router(use_cases_of_request: Callable[..., TenantUseCases]) -> APIRouter:
    router = APIRouter(tags=["flussi"])

    @router.post("/flows", status_code=status.HTTP_201_CREATED)
    def create_flow(
        request: FlowCreationRequest, use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)]
    ) -> FlowResponse:
        return FlowResponse.of(use_cases.create_flow.execute(request.command()))

    @router.get("/flows")
    def list_flows(use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)]) -> list[FlowResponse]:
        return [FlowResponse.of(flow) for flow in use_cases.list_flows.execute()]

    @router.get("/accounts/{account_id}/free-capital")
    def read_free_capital(
        account_id: UUID, use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)]
    ) -> FreeCapitalResponse:
        return FreeCapitalResponse.of(use_cases.read_free_capital.execute(ReadFreeCapitalCommand(account_id)))

    return router


def _text(value: Decimal | None) -> str | None:
    return None if value is None else str(value)
