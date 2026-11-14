from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from autotrading.adapters.inbound.api.tenant_use_cases import TenantUseCases
from autotrading.application.agent.ports import ProviderKeyRegistration
from autotrading.application.agent.register_provider_key import RegisterProviderKeyCommand
from autotrading.application.agent.remove_provider_key import RemoveProviderKeyCommand
from autotrading.application.agent.replace_provider_key import ReplaceProviderKeyCommand


class ProviderKeyRegistrationRequest(BaseModel):
    # Missing values arrive empty, so the domain answers with the reason of the requirement.
    provider: str = ""
    key: str = ""

    def __repr_args__(self) -> list[tuple[str | None, object]]:
        return [("provider", self.provider)]


class ProviderKeyReplacementRequest(BaseModel):
    key: str = ""

    def __repr_args__(self) -> list[tuple[str | None, object]]:
        return []


class ProviderKeyResponse(BaseModel):
    """A registered key as its owner reads it: the provider and when it was saved, never the key (R1.4.1, ADR 0130)."""

    provider: str
    registered_at: str

    @classmethod
    def of(cls, registration: ProviderKeyRegistration) -> ProviderKeyResponse:
        return cls(provider=registration.provider.value, registered_at=registration.registered_at.isoformat())


def provider_keys_router(use_cases_of_request: Callable[..., TenantUseCases]) -> APIRouter:
    router = APIRouter(prefix="/provider-keys", tags=["chiavi dei fornitori IA"])

    @router.post("", status_code=status.HTTP_201_CREATED)
    def register_provider_key(
        request: ProviderKeyRegistrationRequest, use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)]
    ) -> ProviderKeyResponse:
        command = RegisterProviderKeyCommand(request.provider, request.key)
        return ProviderKeyResponse.of(use_cases.register_provider_key.execute(command))

    @router.get("")
    def list_provider_keys(
        use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)],
    ) -> list[ProviderKeyResponse]:
        return [ProviderKeyResponse.of(registration) for registration in use_cases.list_provider_keys.execute()]

    @router.put("/{provider}")
    def replace_provider_key(
        provider: str,
        request: ProviderKeyReplacementRequest,
        use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)],
    ) -> ProviderKeyResponse:
        command = ReplaceProviderKeyCommand(provider, request.key)
        return ProviderKeyResponse.of(use_cases.replace_provider_key.execute(command))

    @router.delete("/{provider}", status_code=status.HTTP_204_NO_CONTENT)
    def remove_provider_key(provider: str, use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)]) -> None:
        use_cases.remove_provider_key.execute(RemoveProviderKeyCommand(provider))

    return router
