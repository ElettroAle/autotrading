from collections.abc import Callable
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from autotrading.adapters.inbound.api.flows import PositionLeftOpenResponse
from autotrading.adapters.inbound.api.tenant_use_cases import TenantUseCases
from autotrading.application.flows.close_in_emergency import CloseInEmergencyCommand
from autotrading.application.flows.preview_emergency_closing import PreviewEmergencyClosingCommand
from autotrading.domain.flows.emergency_closing import (
    EmergencyClosing,
    EmergencyClosingPreview,
    EmergencyScope,
    EmergencyScopeKind,
    FlowEmergencyOutcome,
)
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.tenancy.user_id import UserId


class EmergencyClosingRequest(BaseModel):
    """A flow, an account, or neither for every flow of the user (R3.2.3)."""

    flow_id: UUID | None = None
    account_id: UUID | None = None

    def scope(self) -> EmergencyScope:
        return _scope_of(self.flow_id, self.account_id)


class EmergencyScopeResponse(BaseModel):
    kind: EmergencyScopeKind
    flow_id: UUID | None
    account_id: UUID | None

    @classmethod
    def of(cls, scope: EmergencyScope) -> EmergencyScopeResponse:
        flow_id = None if scope.flow_id is None else scope.flow_id.value
        return cls(kind=scope.kind, flow_id=flow_id, account_id=scope.account_id)


class FlowEmergencyOutcomeResponse(BaseModel):
    """What the closing did to one flow: the assets closed, the positions left open with the reason of the exchange,
    the reason the whole flow failed, or the remark that it had nothing to close (R3.2.3)."""

    flow_id: UUID
    flow_name: str
    closed: list[str]
    left_open: list[PositionLeftOpenResponse]
    failure: str | None
    remark: str | None

    @classmethod
    def of(cls, outcome: FlowEmergencyOutcome) -> FlowEmergencyOutcomeResponse:
        return cls(
            flow_id=outcome.flow_id.value,
            flow_name=outcome.flow_name,
            closed=list(outcome.closed),
            left_open=[PositionLeftOpenResponse.of(position) for position in outcome.left_open],
            failure=outcome.failure,
            remark=outcome.remark,
        )


class EmergencyClosingResponse(BaseModel):
    closed_at: datetime
    scope: EmergencyScopeResponse
    flows: list[FlowEmergencyOutcomeResponse]

    @classmethod
    def of(cls, closing: EmergencyClosing) -> EmergencyClosingResponse:
        return cls(
            closed_at=closing.closed_at,
            scope=EmergencyScopeResponse.of(closing.scope),
            flows=[FlowEmergencyOutcomeResponse.of(outcome) for outcome in closing.outcomes],
        )


class EmergencyClosingPreviewResponse(BaseModel):
    """The flows of the scope and the positions they hold now, for the confirmation (ADR chiusura-di-emergenza-nella-
    dashboard)."""

    flows: int
    positions: int

    @classmethod
    def of(cls, preview: EmergencyClosingPreview) -> EmergencyClosingPreviewResponse:
        return cls(flows=preview.flows, positions=preview.positions)


def emergency_closings_router(
    use_cases_of_request: Callable[..., TenantUseCases], user_of_request: Callable[..., UserId]
) -> APIRouter:
    router = APIRouter(tags=["flussi"])

    @router.post("/flows/emergency-closings")
    def close_in_emergency(
        request: EmergencyClosingRequest,
        use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)],
        user_id: Annotated[UserId, Depends(user_of_request)],
    ) -> EmergencyClosingResponse:
        command = CloseInEmergencyCommand(request.scope(), user_id)
        return EmergencyClosingResponse.of(use_cases.close_in_emergency.execute(command))

    @router.get("/flows/emergency-closings/preview")
    def preview_emergency_closing(
        use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)],
        flow_id: UUID | None = None,
        account_id: UUID | None = None,
    ) -> EmergencyClosingPreviewResponse:
        command = PreviewEmergencyClosingCommand(_scope_of(flow_id, account_id))
        return EmergencyClosingPreviewResponse.of(use_cases.preview_emergency_closing.execute(command))

    return router


def _scope_of(flow_id: UUID | None, account_id: UUID | None) -> EmergencyScope:
    return EmergencyScope(flow_id=None if flow_id is None else FlowId(flow_id), account_id=account_id)
