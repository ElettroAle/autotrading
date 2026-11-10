from collections.abc import Callable
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from autotrading.adapters.inbound.api.order_outcome import OrderOutcomeResponse
from autotrading.adapters.inbound.api.tenant_use_cases import TenantUseCases
from autotrading.application.orders.close_position import ClosePositionCommand
from autotrading.domain.orders.errors import ManualOpeningNotAllowedError
from autotrading.domain.tenancy.user_id import UserId


def orders_router(
    use_cases_of_request: Callable[..., TenantUseCases], user_of_request: Callable[..., UserId]
) -> APIRouter:
    router = APIRouter(prefix="/accounts/{account_id}/positions", tags=["posizioni"])

    @router.post("/{coin}/close")
    def close_position(
        account_id: UUID,
        coin: str,
        use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)],
        user_id: Annotated[UserId, Depends(user_of_request)],
    ) -> OrderOutcomeResponse:
        # The outcome is the answer, even when the exchange refuses the order (R0.3.3, ADR 0023).
        command = ClosePositionCommand(account_id, coin, user_id)
        return OrderOutcomeResponse.of(use_cases.close_position.execute(command))

    @router.post("", responses={403: {"description": "apertura manuale non consentita"}})
    def open_position() -> None:
        # Only the procedure of verification and the flows open positions (R0.3.2): a user is always refused.
        raise ManualOpeningNotAllowedError

    return router
