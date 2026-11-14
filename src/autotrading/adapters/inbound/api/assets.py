from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends

from autotrading.adapters.inbound.api.tenant_use_cases import TenantUseCases


def assets_router(use_cases_of_request: Callable[..., TenantUseCases]) -> APIRouter:
    router = APIRouter(prefix="/assets", tags=["flussi"])

    @router.get("", responses={503: {"description": "exchange non raggiungibile"}})
    def list_tradable_assets(use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)]) -> list[str]:
        """The assets a flow can trade now on the exchange of the installation, by name (ADR 0147)."""
        return list(use_cases.list_tradable_assets.execute())

    return router
