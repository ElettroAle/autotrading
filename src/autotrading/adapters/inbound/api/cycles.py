from collections.abc import Callable
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from autotrading.adapters.inbound.api.amounts import amount_text
from autotrading.adapters.inbound.api.tenant_use_cases import TenantUseCases
from autotrading.application.flows.list_cycles import ListCyclesCommand
from autotrading.application.flows.list_flow_overviews import FlowOverview
from autotrading.application.flows.read_cycle import ReadCycleCommand
from autotrading.application.flows.read_flow_cost import ReadFlowCostCommand
from autotrading.domain.flows.call_cost import CallCost
from autotrading.domain.flows.cycle_page import CyclePage
from autotrading.domain.flows.cycle_record import CycleFailure, CycleRecord
from autotrading.domain.flows.cycle_step import CycleStep
from autotrading.domain.flows.flow_cost import FlowCost


class FailureResponse(BaseModel):
    step: str
    error_type: str
    message: str

    @classmethod
    def of(cls, failure: CycleFailure | None) -> FailureResponse | None:
        if failure is None:
            return None
        return cls(step=failure.step.value, error_type=failure.error_type, message=failure.message)


class CallCostResponse(BaseModel):
    input_tokens: int
    output_tokens: int
    # Numbers travel as strings, so no precision is lost on the way (ADR 0018); empty when nobody knows the cost.
    cost_usd: str | None

    @classmethod
    def of(cls, cost: CallCost | None) -> CallCostResponse | None:
        if cost is None:
            return None
        return cls(input_tokens=cost.input_tokens, output_tokens=cost.output_tokens, cost_usd=_text(cost.cost_usd))


class CycleSummaryResponse(BaseModel):
    """A cycle in the list: its instants, its outcome and the decisions of the agent (R1.7.3)."""

    planned_at: datetime
    started_at: datetime | None
    outcome: str
    failure: FailureResponse | None
    decisions: dict[str, object] | None

    @classmethod
    def of(cls, record: CycleRecord) -> CycleSummaryResponse:
        decisions = record.document(CycleStep.AGENT_DECISION)
        return cls(
            planned_at=record.planned_at,
            started_at=record.started_at,
            outcome=record.outcome.value,
            failure=FailureResponse.of(record.failure),
            decisions=None if decisions is None else dict(decisions),
        )


class CyclePageResponse(BaseModel):
    page: int
    has_next: bool
    cycles: list[CycleSummaryResponse]

    @classmethod
    def of(cls, page: CyclePage) -> CyclePageResponse:
        return cls(
            page=page.number, has_next=page.has_next, cycles=[CycleSummaryResponse.of(cycle) for cycle in page.cycles]
        )


class StepDocumentResponse(BaseModel):
    step: str
    content: dict[str, object]


class AbsentSourceResponse(BaseModel):
    source: str
    reason: str


class CycleDetailResponse(BaseModel):
    """A cycle with everything recorded about it (R1.7.1)."""

    planned_at: datetime
    started_at: datetime | None
    delay_seconds: int | None
    outcome: str
    failure: FailureResponse | None
    steps: list[str]
    absent_sources: list[AbsentSourceResponse]
    documents: list[StepDocumentResponse]
    cost: CallCostResponse | None

    @classmethod
    def of(cls, record: CycleRecord) -> CycleDetailResponse:
        return cls(
            planned_at=record.planned_at,
            started_at=record.started_at,
            delay_seconds=record.delay_seconds,
            outcome=record.outcome.value,
            failure=FailureResponse.of(record.failure),
            steps=[step.value for step in record.steps],
            absent_sources=[
                AbsentSourceResponse(source=item.source, reason=item.reason) for item in record.absent_sources
            ],
            documents=[
                StepDocumentResponse(step=document.step.value, content=dict(document.content))
                for document in record.documents
            ],
            cost=CallCostResponse.of(record.cost),
        )


class DailyCostResponse(BaseModel):
    day: date
    cost_usd: str


class FlowCostResponse(BaseModel):
    total_usd: str
    days: list[DailyCostResponse]
    unavailable_calls: int

    @classmethod
    def of(cls, cost: FlowCost) -> FlowCostResponse:
        return cls(
            total_usd=str(cost.total_usd),
            days=[DailyCostResponse(day=day.day, cost_usd=str(day.cost_usd)) for day in cost.days],
            unavailable_calls=cost.unavailable_calls,
        )


class LastCycleResponse(BaseModel):
    planned_at: datetime
    outcome: str

    @classmethod
    def of(cls, record: CycleRecord | None) -> LastCycleResponse | None:
        if record is None:
            return None
        return cls(planned_at=record.planned_at, outcome=record.outcome.value)


class FlowOverviewResponse(BaseModel):
    """A flow in use with its last cycle, the next planned one, the outcomes of its last ten cycles from the most
    recent and how its capital is doing (R1.7.3, R2.2.2, ADR 0127).
    """

    id: UUID
    name: str
    account: str
    environment: str
    status: str
    pause_reason: str | None
    model: str
    last_cycle: LastCycleResponse | None
    next_cycle_at: datetime | None
    # Empty for a draft, which has no account yet (ADR 0124).
    currency: str | None
    # Amounts travel as strings (ADR 0018); the return keeps its two decimals and is empty without initial capital.
    initial_capital: str | None
    current_capital: str | None
    return_percent: str | None
    recent_outcomes: list[LastCycleResponse]

    @classmethod
    def of(cls, overview: FlowOverview) -> FlowOverviewResponse:
        summary, capital = overview.summary, overview.capital
        return cls(
            id=summary.flow_id,
            name=summary.name,
            account=summary.account,
            environment=overview.environment,
            status=summary.status,
            pause_reason=summary.pause_reason,
            model=summary.model,
            last_cycle=LastCycleResponse.of(overview.last_cycle),
            next_cycle_at=overview.next_cycle_at,
            currency=overview.currency,
            initial_capital=None if capital is None else amount_text(capital.initial_capital),
            current_capital=None if capital is None else amount_text(capital.current_capital),
            return_percent=None if capital is None else _text(capital.percent),
            recent_outcomes=[
                LastCycleResponse(planned_at=record.planned_at, outcome=record.outcome.value)
                for record in overview.recent_cycles
            ],
        )


def cycles_router(use_cases_of_request: Callable[..., TenantUseCases]) -> APIRouter:
    router = APIRouter(tags=["cicli"])

    @router.get("/flows/overview")
    def list_flow_overviews(
        use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)],
    ) -> list[FlowOverviewResponse]:
        return [FlowOverviewResponse.of(overview) for overview in use_cases.list_flow_overviews.execute()]

    @router.get("/flows/{flow_id}/cycles")
    def list_cycles(
        flow_id: UUID,
        use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)],
        page: Annotated[int, Query()] = 1,
    ) -> CyclePageResponse:
        return CyclePageResponse.of(use_cases.list_cycles.execute(ListCyclesCommand(flow_id, page)))

    @router.get("/flows/{flow_id}/cycles/{planned_at}")
    def read_cycle(
        flow_id: UUID, planned_at: datetime, use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)]
    ) -> CycleDetailResponse:
        return CycleDetailResponse.of(use_cases.read_cycle.execute(ReadCycleCommand(flow_id, planned_at)))

    @router.get("/flows/{flow_id}/cost")
    def read_flow_cost(
        flow_id: UUID, use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)]
    ) -> FlowCostResponse:
        return FlowCostResponse.of(use_cases.read_flow_cost.execute(ReadFlowCostCommand(flow_id)))

    return router


def _text(value: Decimal | None) -> str | None:
    return None if value is None else str(value)
