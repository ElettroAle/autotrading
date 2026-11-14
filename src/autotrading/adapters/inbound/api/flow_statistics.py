from collections.abc import Callable
from datetime import date
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from autotrading.adapters.inbound.api.amounts import amount_text
from autotrading.adapters.inbound.api.tenant_use_cases import TenantUseCases
from autotrading.application.flows.read_flow_statistics import ReadFlowStatisticsCommand
from autotrading.domain.flows.flow_statistics import FlowStatistics

TWO_DECIMALS = Decimal("0.01")


class FlowStatisticsResponse(BaseModel):
    """The statistics of a flow over a period (R2.2.6): amounts as text (ADR 0018), win rate in percent with two
    decimals, null when nothing is available (ADR 0122).
    """

    won: int
    lost: int
    operations: int
    win_rate_percent: str | None
    average_winning_pnl: str | None
    average_losing_pnl: str | None
    total_fees: str
    model_cost_usd: str
    model_calls_without_cost: int

    @classmethod
    def of(cls, statistics: FlowStatistics) -> FlowStatisticsResponse:
        rate = statistics.win_rate_percent
        return cls(
            won=statistics.won,
            lost=statistics.lost,
            operations=statistics.operations,
            win_rate_percent=None if rate is None else str(rate.quantize(TWO_DECIMALS)),
            average_winning_pnl=_optional_amount(statistics.average_winning_pnl),
            average_losing_pnl=_optional_amount(statistics.average_losing_pnl),
            total_fees=amount_text(statistics.total_fees),
            model_cost_usd=amount_text(statistics.model_cost_usd),
            model_calls_without_cost=statistics.model_calls_without_cost,
        )


def flow_statistics_router(use_cases_of_request: Callable[..., TenantUseCases]) -> APIRouter:
    router = APIRouter(tags=["flussi"])

    @router.get("/flows/{flow_id}/statistics")
    def read_flow_statistics(
        flow_id: UUID,
        use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)],
        period: Annotated[str, Query(description="all, 7d, 30d o range")] = "all",
        first_day: Annotated[date | None, Query(alias="from", description="primo giorno di un intervallo")] = None,
        last_day: Annotated[date | None, Query(alias="to", description="ultimo giorno di un intervallo")] = None,
    ) -> FlowStatisticsResponse:
        command = ReadFlowStatisticsCommand(flow_id, period, first_day, last_day)
        return FlowStatisticsResponse.of(use_cases.read_flow_statistics.execute(command))

    return router


def _optional_amount(amount: Decimal | None) -> str | None:
    return None if amount is None else amount_text(amount)
