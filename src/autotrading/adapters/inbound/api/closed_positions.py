from collections.abc import Callable
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from autotrading.adapters.inbound.api.amounts import amount_text
from autotrading.adapters.inbound.api.tenant_use_cases import TenantUseCases
from autotrading.application.flows.list_closed_positions import ListClosedPositionsCommand
from autotrading.domain.flows.closed_position import ClosedPosition
from autotrading.domain.flows.closed_position_page import ClosedPositionPage


class ClosedPositionResponse(BaseModel):
    """A closed position of a flow with its result (R1.7.2); amounts as text without trailing zeros (ADR 0018)."""

    asset: str
    side: str
    leverage: int
    margin: str
    open_price: str
    close_price: str
    opened_at: datetime
    closed_at: datetime
    duration_seconds: int
    pnl: str
    pnl_percent_of_margin: str
    fees: str
    reason: str
    opening_cycle: datetime | None
    closing_cycle: datetime | None

    @classmethod
    def of(cls, position: ClosedPosition) -> ClosedPositionResponse:
        return cls(
            asset=position.asset,
            side=position.side.value,
            leverage=position.leverage,
            margin=amount_text(position.margin),
            open_price=amount_text(position.opening.price),
            close_price=amount_text(position.closing.price),
            opened_at=position.opening.at,
            closed_at=position.closing.at,
            duration_seconds=int(position.duration.total_seconds()),
            pnl=amount_text(position.pnl),
            pnl_percent_of_margin=amount_text(position.pnl_percent_of_margin),
            fees=amount_text(position.fees),
            reason=position.reason.value,
            opening_cycle=position.opening.cycle,
            closing_cycle=position.closing.cycle,
        )


class ClosedPositionPageResponse(BaseModel):
    """A page of the closed positions of a flow, from the most recent close (R1.7.2, R2.2.5)."""

    page: int
    has_next: bool
    positions: list[ClosedPositionResponse]

    @classmethod
    def of(cls, page: ClosedPositionPage) -> ClosedPositionPageResponse:
        return cls(
            page=page.number,
            has_next=page.has_next,
            positions=[ClosedPositionResponse.of(position) for position in page.positions],
        )


def closed_positions_router(use_cases_of_request: Callable[..., TenantUseCases]) -> APIRouter:
    router = APIRouter(tags=["flussi"])

    @router.get("/flows/{flow_id}/closed-positions")
    def list_closed_positions(
        flow_id: UUID,
        use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)],
        page: Annotated[int, Query()] = 1,
    ) -> ClosedPositionPageResponse:
        command = ListClosedPositionsCommand(flow_id, page)
        return ClosedPositionPageResponse.of(use_cases.list_closed_positions.execute(command))

    return router
