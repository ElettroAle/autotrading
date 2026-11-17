from collections.abc import Callable
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from autotrading.adapters.inbound.api.tenant_use_cases import TenantUseCases
from autotrading.application.flows.read_last_decision import ReadLastDecisionCommand
from autotrading.domain.flows.recorded_decision import DecidedCycle, RecordedDecision


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


def decisions_router(use_cases_of_request: Callable[..., TenantUseCases]) -> APIRouter:
    router = APIRouter(tags=["flussi"])

    @router.get("/flows/{flow_id}/decisions/latest")
    def read_last_decision(
        flow_id: UUID, use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)]
    ) -> LastDecisionResponse | None:
        """The last decision of the flow, whatever the period; null before its first completed cycle with one."""
        cycle = use_cases.read_last_decision.execute(ReadLastDecisionCommand(flow_id))
        return LastDecisionResponse.of(cycle)

    return router
