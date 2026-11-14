from collections.abc import Callable
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from autotrading.adapters.inbound.api.amounts import amount_text
from autotrading.adapters.inbound.api.tenant_use_cases import TenantUseCases
from autotrading.application.flows.read_flow_state import ReadFlowStateCommand
from autotrading.domain.flows.account_activity import AccountPosition
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.flow_state import FlowState


class FlowPositionResponse(BaseModel):
    """An open position of the flow (R1.6.1, R2.2.4); the percent is absent for a position without margin."""

    asset: str
    side: str
    size: str
    leverage: str
    entry_price: str
    margin: str
    unrealized_pnl: str
    unrealized_pnl_percent: str | None

    @classmethod
    def of(cls, position: AccountPosition) -> FlowPositionResponse:
        percent = position.unrealized_pnl_percent
        return cls(
            asset=position.asset,
            side=position.side.value,
            size=amount_text(position.size),
            leverage=str(position.leverage),
            entry_price=amount_text(position.entry_price),
            margin=amount_text(position.margin),
            unrealized_pnl=amount_text(position.unrealized_pnl),
            unrealized_pnl_percent=None if percent is None else amount_text(percent),
        )


class FlowStateResponse(BaseModel):
    """The state of a flow attributed from the exchange at the request (R1.6.1); amounts as strings (ADR 0018)."""

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

    @classmethod
    def of(cls, state: FlowState) -> FlowStateResponse:
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
            positions=[FlowPositionResponse.of(position) for position in state.positions],
        )


def flow_state_router(use_cases_of_request: Callable[..., TenantUseCases]) -> APIRouter:
    router = APIRouter(tags=["flussi"])

    @router.get("/flows/{flow_id}/state")
    def read_flow_state(
        flow_id: UUID, use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)]
    ) -> FlowStateResponse:
        return FlowStateResponse.of(use_cases.read_flow_state.execute(ReadFlowStateCommand(FlowId(flow_id))))

    return router
