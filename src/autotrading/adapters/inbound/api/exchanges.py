from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends

from autotrading.adapters.inbound.api.tenant_use_cases import TenantUseCases


def exchanges_router(use_cases_of_request: Callable[..., TenantUseCases]) -> APIRouter:
    router = APIRouter(prefix="/exchanges", tags=["conti"])

    @router.get("")
    def list_supported_exchanges(use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)]) -> list[str]:
        """The exchanges an account can be registered on, by name (ADR 0152)."""
        return list(use_cases.list_supported_exchanges.execute())

    return router
