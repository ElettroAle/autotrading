from collections.abc import Callable
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from autotrading.adapters.inbound.api.history import period_of
from autotrading.adapters.inbound.api.tenant_use_cases import TenantUseCases
from autotrading.application.flows.list_decisions import ListDecisionsCommand
from autotrading.application.flows.read_last_decision import ReadLastDecisionCommand
from autotrading.domain.flows.decision_filter import DecisionFilter
from autotrading.domain.flows.decision_page import DecisionPage
from autotrading.domain.flows.recorded_decision import DatedDecision, DecidedCycle, RecordedDecision
from autotrading.domain.flows.statistics_period import StatisticsPeriod


class DecisionResponse(BaseModel):
    """A decision of the agent on one asset: the direction only for an opening, the confidence null when the agent
    gave none (R6.5.4).
    """

    asset: str
    action: str
    direction: str | None
    confidence: int | None
    reasoning: str

    @classmethod
    def of(cls, decision: RecordedDecision) -> DecisionResponse:
        return cls(
            asset=decision.asset,
            action=decision.action.value,
            direction=None if decision.direction is None else decision.direction.value,
            confidence=decision.confidence,
            reasoning=decision.reasoning,
        )


class LastDecisionResponse(BaseModel):
    """The last decision of the agent in the flow: the planned instant of its cycle and its decisions, one by asset
    (ADR decisioni-del-ciclo-registrate-per-asset).
    """

    planned_at: datetime
    decisions: list[DecisionResponse]

    @classmethod
    def of(cls, cycle: DecidedCycle | None) -> LastDecisionResponse | None:
        if cycle is None:
            return None
        return cls(planned_at=cycle.planned_at, decisions=[DecisionResponse.of(each) for each in cycle.decisions])


class DatedDecisionResponse(DecisionResponse):
    """A decision of the history with the planned instant of its cycle, which leads to its detail (R6.5.5)."""

    planned_at: datetime

    @classmethod
    def dated(cls, entry: DatedDecision) -> DatedDecisionResponse:
        return cls(planned_at=entry.planned_at, **DecisionResponse.of(entry.decision).model_dump())


class DecisionPageResponse(BaseModel):
    """A page of the decisions that match the filters in the period, with how many match in all (ADR
    storico-delle-decisioni-nell-api).
    """

    page: int
    has_next: bool
    total: int
    decisions: list[DatedDecisionResponse]

    @classmethod
    def of(cls, page: DecisionPage) -> DecisionPageResponse:
        return cls(
            page=page.number,
            has_next=page.has_next,
            total=page.total,
            decisions=[DatedDecisionResponse.dated(entry) for entry in page.decisions],
        )


def decision_filter_of(
    asset: Annotated[str | None, Query(description="un asset del flusso")] = None,
    action: Annotated[str | None, Query(description="apri, chiudi, mantieni, aggiorna o inverti")] = None,
    direction: Annotated[str | None, Query(description="long o short")] = None,
) -> DecisionFilter:
    """The filters of the history of the decisions, in any combination (R6.5.5)."""
    return DecisionFilter.named(asset, action, direction)


def decisions_router(use_cases_of_request: Callable[..., TenantUseCases]) -> APIRouter:
    router = APIRouter(tags=["flussi"])

    @router.get("/flows/{flow_id}/decisions")
    def list_decisions(
        flow_id: UUID,
        use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)],
        criteria: Annotated[DecisionFilter, Depends(decision_filter_of)],
        period: Annotated[StatisticsPeriod, Depends(period_of)],
        page: Annotated[int, Query()] = 1,
    ) -> DecisionPageResponse:
        """The decisions of the completed cycles of the flow in the period, one by cycle and asset, newest first."""
        command = ListDecisionsCommand(flow_id, page, criteria, period)
        return DecisionPageResponse.of(use_cases.list_decisions.execute(command))

    @router.get("/flows/{flow_id}/decisions/latest")
    def read_last_decision(
        flow_id: UUID, use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)]
    ) -> LastDecisionResponse | None:
        """The last decision of the flow, whatever the period; null before its first completed cycle with one."""
        cycle = use_cases.read_last_decision.execute(ReadLastDecisionCommand(flow_id))
        return LastDecisionResponse.of(cycle)

    return router
