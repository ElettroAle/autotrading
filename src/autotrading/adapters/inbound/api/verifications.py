from collections.abc import Callable
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from autotrading.adapters.inbound.api.tenant_use_cases import TenantUseCases
from autotrading.adapters.inbound.api.verification_run import VerificationRunResponse
from autotrading.application.verification.run_verification import RunVerificationCommand
from autotrading.domain.tenancy.user_id import UserId


def verifications_router(
    use_cases_of_request: Callable[..., TenantUseCases], user_of_request: Callable[..., UserId]
) -> APIRouter:
    router = APIRouter(prefix="/accounts/{account_id}/verifications", tags=["procedura di verifica"])

    @router.post("", responses={409: {"description": "la procedura non parte"}})
    def run_verification(
        account_id: UUID,
        use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)],
        user_id: Annotated[UserId, Depends(user_of_request)],
    ) -> VerificationRunResponse:
        # A failed procedure is still the answer: its steps say where it stopped (R0.4.1, ADR 0024).
        run = use_cases.run_verification.execute(RunVerificationCommand(account_id, user_id))
        return VerificationRunResponse.of(run)

    return router
