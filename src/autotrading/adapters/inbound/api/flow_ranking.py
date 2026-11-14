from collections.abc import Callable
from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from autotrading.adapters.inbound.api.amounts import amount_text
from autotrading.adapters.inbound.api.tenant_use_cases import TenantUseCases
from autotrading.application.flows.rank_flows import RankFlowsCommand
from autotrading.domain.flows.flow_ranking import FlowRanking

TWO_DECIMALS = Decimal("0.01")


class FlowRankingResponse(BaseModel):
    """A row of the ranking of the flows (R2.4.2): amounts as text (ADR 0018), percentages with two decimals, null
    when not available (ADR 0135).
    """

    flow_id: str
    flow_name: str
    return_percent: str | None
    max_drawdown_percent: str
    pnl: str
    total_fees: str
    win_rate_percent: str | None
    operations: int
    model_cost_usd: str
    model_calls_without_cost: int

    @classmethod
    def of(cls, ranking: FlowRanking) -> FlowRankingResponse:
        statistics = ranking.statistics
        return cls(
            flow_id=str(ranking.flow_id),
            flow_name=ranking.flow_name,
            return_percent=_optional_percent(ranking.return_percent),
            max_drawdown_percent=_percent(ranking.max_drawdown_percent),
            pnl=amount_text(statistics.net_pnl),
            total_fees=amount_text(statistics.total_fees),
            win_rate_percent=_optional_percent(statistics.win_rate_percent),
            operations=statistics.operations,
            model_cost_usd=amount_text(statistics.model_cost_usd),
            model_calls_without_cost=statistics.model_calls_without_cost,
        )


def flow_ranking_router(use_cases_of_request: Callable[..., TenantUseCases]) -> APIRouter:
    router = APIRouter(tags=["flussi"])

    @router.get("/flows/ranking")
    def rank_flows(
        use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)],
        period: Annotated[str, Query(description="all, 7d, 30d o range")] = "all",
        first_day: Annotated[date | None, Query(alias="from", description="primo giorno di un intervallo")] = None,
        last_day: Annotated[date | None, Query(alias="to", description="ultimo giorno di un intervallo")] = None,
    ) -> list[FlowRankingResponse]:
        command = RankFlowsCommand(period, first_day, last_day)
        return [FlowRankingResponse.of(ranking) for ranking in use_cases.rank_flows.execute(command)]

    return router


def _percent(value: Decimal) -> str:
    return str(value.quantize(TWO_DECIMALS))


def _optional_percent(value: Decimal | None) -> str | None:
    return None if value is None else _percent(value)
