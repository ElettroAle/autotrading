from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from autotrading.adapters.inbound.api.tenant_use_cases import TenantUseCases
from autotrading.application.accounts.list_supported_exchanges import SupportedExchange


class ExchangeResponse(BaseModel):
    name: str
    network: str

    @classmethod
    def of(cls, exchange: SupportedExchange) -> ExchangeResponse:
        return cls(name=exchange.name, network=exchange.network.value)


def exchanges_router(use_cases_of_request: Callable[..., TenantUseCases]) -> APIRouter:
    router = APIRouter(prefix="/exchanges", tags=["conti"])

    @router.get("")
    def list_supported_exchanges(
        use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)],
    ) -> list[ExchangeResponse]:
        """The exchanges an account can be registered on, each with the network it trades on (ADR 0152, ADR 0157)."""
        return [ExchangeResponse.of(exchange) for exchange in use_cases.list_supported_exchanges.execute()]

    return router
