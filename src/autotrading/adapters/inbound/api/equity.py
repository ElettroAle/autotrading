from collections.abc import Callable
from datetime import date, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from autotrading.adapters.inbound.api.amounts import amount_text
from autotrading.adapters.inbound.api.tenant_use_cases import TenantUseCases
from autotrading.application.flows.read_flow_equity import ReadFlowEquityCommand
from autotrading.domain.flows.equity_snapshot import EquitySnapshot, FlowEquity


class EquityPointResponse(BaseModel):
    planned_at: datetime
    equity: str

    @classmethod
    def of(cls, snapshot: EquitySnapshot) -> EquityPointResponse:
        return cls(planned_at=snapshot.planned_at, equity=amount_text(snapshot.equity))


class FlowEquityResponse(BaseModel):
    """The equity curve of a flow: a point for each cycle, from the oldest, and the capital it is judged against
    (R2.2.3); amounts as text without trailing zeros (ADR 0018).
    """

    initial_capital: str
    points: list[EquityPointResponse]

    @classmethod
    def of(cls, equity: FlowEquity) -> FlowEquityResponse:
        return cls(
            initial_capital=amount_text(equity.initial_capital),
            points=[EquityPointResponse.of(snapshot) for snapshot in equity.snapshots],
        )


def equity_router(use_cases_of_request: Callable[..., TenantUseCases]) -> APIRouter:
    router = APIRouter(tags=["flussi"])

    @router.get("/flows/{flow_id}/equity")
    def read_flow_equity(
        flow_id: UUID,
        use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)],
        period: Annotated[str, Query(description="all, 7d, 30d o range")] = "all",
        first_day: Annotated[date | None, Query(alias="from", description="primo giorno di un intervallo")] = None,
        last_day: Annotated[date | None, Query(alias="to", description="ultimo giorno di un intervallo")] = None,
    ) -> FlowEquityResponse:
        command = ReadFlowEquityCommand(flow_id, period, first_day, last_day)
        return FlowEquityResponse.of(use_cases.read_flow_equity.execute(command))

    return router
