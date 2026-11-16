from collections.abc import Callable
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from autotrading.adapters.inbound.api.amounts import amount_text
from autotrading.adapters.inbound.api.flow_results import FlowResultsResponse
from autotrading.adapters.inbound.api.flows import OpeningsSuspensionResponse
from autotrading.adapters.inbound.api.interval_query import IntervalEnd, IntervalStart
from autotrading.adapters.inbound.api.tenant_use_cases import TenantUseCases
from autotrading.application.flows.read_flow_results import ReadFlowResultsCommand
from autotrading.domain.flows.account_activity import AccountPosition
from autotrading.domain.flows.exit_plan import ExitPlan
from autotrading.domain.flows.flow_results import FlowResults


class FlowPositionResponse(BaseModel):
    """An open position of the flow (R1.6.1, R2.2.4) with its exit plan in force (R3.1.1); the percent is absent for a
    position without margin, each level of the plan when the agent declared none.
    """

    asset: str
    side: str
    size: str
    leverage: str
    entry_price: str
    mark_price: str
    margin: str
    unrealized_pnl: str
    unrealized_pnl_percent: str | None
    target_price: str | None
    stop_price: str | None
    invalidation: str | None

    @classmethod
    def of(cls, position: AccountPosition, plan: ExitPlan) -> FlowPositionResponse:
        percent = position.unrealized_pnl_percent
        return cls(
            asset=position.asset,
            side=position.side.value,
            size=amount_text(position.size),
            leverage=str(position.leverage),
            entry_price=amount_text(position.entry_price),
            mark_price=amount_text(position.mark_price),
            margin=amount_text(position.margin),
            unrealized_pnl=amount_text(position.unrealized_pnl),
            unrealized_pnl_percent=None if percent is None else amount_text(percent),
            target_price=_price_text(plan.target),
            stop_price=_price_text(plan.stop),
            invalidation=plan.invalidation,
        )


class FlowStateResponse(BaseModel):
    """The state of a flow attributed from the exchange at the request (R1.6.1), with its results in the period asked
    for (R6.4.2) and why its openings are suspended, null when they are not (R3.3.2); amounts as strings (ADR 0018).
    """

    flow_id: UUID
    currency: str
    allocated_capital: str
    available_liquidity: str
    margin: str
    unrealized_pnl: str
    realized_pnl: str
    fees: str
    total_value: str
    return_percent: str
    positions: list[FlowPositionResponse]
    summary: FlowResultsResponse
    openings_suspension: OpeningsSuspensionResponse | None

    @classmethod
    def of(cls, results: FlowResults) -> FlowStateResponse:
        state = results.state
        return cls(
            flow_id=state.flow_id.value,
            currency=state.currency,
            allocated_capital=amount_text(state.allocated_capital),
            available_liquidity=amount_text(state.available_liquidity),
            margin=amount_text(state.margin),
            unrealized_pnl=amount_text(state.unrealized_pnl),
            realized_pnl=amount_text(state.realized_pnl),
            fees=amount_text(state.fees),
            total_value=amount_text(state.total_value),
            return_percent=amount_text(state.return_percent),
            positions=[
                FlowPositionResponse.of(position, state.exit_plan_of(position.asset)) for position in state.positions
            ],
            summary=FlowResultsResponse.of(results),
            openings_suspension=OpeningsSuspensionResponse.of(results.openings_suspension),
        )


def flow_state_router(use_cases_of_request: Callable[..., TenantUseCases]) -> APIRouter:
    router = APIRouter(tags=["flussi"])

    @router.get("/flows/{flow_id}/state")
    def read_flow_state(
        flow_id: UUID,
        use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)],
        period: Annotated[str, Query(description="all, 7d, 30d o range")] = "all",
        since: IntervalStart = None,
        until: IntervalEnd = None,
    ) -> FlowStateResponse:
        command = ReadFlowResultsCommand(flow_id, period, since, until)
        return FlowStateResponse.of(use_cases.read_flow_results.execute(command))

    return router


def _price_text(price: Decimal | None) -> str | None:
    return None if price is None else amount_text(price)
