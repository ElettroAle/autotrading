from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from autotrading.adapters.inbound.api.tenant_use_cases import TenantUseCases
from autotrading.application.accounts.list_supported_exchanges import SupportedExchange


class CredentialFieldResponse(BaseModel):
    name: str
    label: str
    secret: bool


class ExchangeResponse(BaseModel):
    name: str
    network: str
    network_name: str
    fields: list[CredentialFieldResponse]
    # False where the exchange reads the expiry of the credentials: the registration does not ask it (R6.2.2).
    expiry_editable: bool

    @classmethod
    def of(cls, exchange: SupportedExchange) -> ExchangeResponse:
        fields = [
            CredentialFieldResponse(name=field.name, label=field.label, secret=field.secret)
            for field in exchange.fields
        ]
        return cls(
            name=exchange.name,
            network=exchange.network.kind.value,
            network_name=exchange.network.name,
            fields=fields,
            expiry_editable=exchange.expiry_editable,
        )


def exchanges_router(use_cases_of_request: Callable[..., TenantUseCases]) -> APIRouter:
    router = APIRouter(prefix="/exchanges", tags=["conti"])

    @router.get("")
    def list_supported_exchanges(
        use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)],
    ) -> list[ExchangeResponse]:
        """The exchanges an account can be registered on, each with its network and the fields of its credentials
        (ADR 0152, ADR 0157, ADR 0158)."""
        return [ExchangeResponse.of(exchange) for exchange in use_cases.list_supported_exchanges.execute()]

    return router
