from collections.abc import Callable
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from autotrading.adapters.inbound.api.key_expiry import ExpiryStatus, KeyExpiryRequest, KeyExpiryResponse
from autotrading.adapters.inbound.api.tenant_use_cases import TenantUseCases
from autotrading.application.agent.ports import ProviderKeyRegistration
from autotrading.application.agent.provider_key_summary import ProviderKeySummary
from autotrading.application.agent.register_provider_key import RegisterProviderKeyCommand
from autotrading.application.agent.remove_provider_key import RemoveProviderKeyCommand
from autotrading.application.agent.replace_provider_key import ReplaceProviderKeyCommand
from autotrading.application.agent.set_provider_key_expiry import SetProviderKeyExpiryCommand


class ProviderKeyRegistrationRequest(BaseModel):
    # Missing values arrive empty, so the domain answers with the reason of the requirement.
    # The key holds the fields its provider declares, by name (R2.3.9): the domain checks them.
    provider: str = ""
    key: dict[str, str] = Field(default_factory=dict)
    # Only when no gateway reads the expiry of the keys of the provider (R6.2.2).
    expires_on: date | None = None

    def __repr_args__(self) -> list[tuple[str | None, object]]:
        return [("provider", self.provider)]


class ProviderKeyReplacementRequest(BaseModel):
    key: dict[str, str] = Field(default_factory=dict)
    expires_on: date | None = None

    def __repr_args__(self) -> list[tuple[str | None, object]]:
        return []


class ProviderKeyResponse(BaseModel):
    """A registered key as its owner reads it: the provider and when it was saved, never the key (R1.4.1, ADR 0130)."""

    provider: str
    registered_at: str

    @classmethod
    def of(cls, registration: ProviderKeyRegistration) -> ProviderKeyResponse:
        return cls(provider=registration.provider.value, registered_at=registration.registered_at.isoformat())


class ProviderKeySummaryResponse(ProviderKeyResponse):
    """A key on the page of the keys: the expiry as of today, with its state (`unknown`, `valid`, `expiring` within 30
    days, `expired`) and the days left, and whether the user may give it (R6.2.2)."""

    expiry: KeyExpiryResponse | None
    expiry_status: ExpiryStatus
    days_left: int | None
    expiry_editable: bool

    @classmethod
    def of_summary(cls, summary: ProviderKeySummary) -> ProviderKeySummaryResponse:
        expiry = summary.expiry
        return cls(
            provider=summary.provider.value,
            registered_at=summary.registered_at.isoformat(),
            expiry=None if expiry is None else KeyExpiryResponse.of(expiry.expires_on, expiry.source),
            expiry_status=ExpiryStatus(summary.reading.status.value),
            days_left=summary.reading.days_left,
            expiry_editable=summary.expiry_editable,
        )


def provider_keys_router(use_cases_of_request: Callable[..., TenantUseCases]) -> APIRouter:
    router = APIRouter(prefix="/provider-keys", tags=["chiavi dei fornitori IA"])

    @router.post("", status_code=status.HTTP_201_CREATED)
    def register_provider_key(
        request: ProviderKeyRegistrationRequest, use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)]
    ) -> ProviderKeyResponse:
        command = RegisterProviderKeyCommand(request.provider, request.key, request.expires_on)
        return ProviderKeyResponse.of(use_cases.register_provider_key.execute(command))

    @router.get("")
    def list_provider_keys(
        use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)],
    ) -> list[ProviderKeySummaryResponse]:
        return [ProviderKeySummaryResponse.of_summary(summary) for summary in use_cases.list_provider_keys.execute()]

    @router.put("/{provider}")
    def replace_provider_key(
        provider: str,
        request: ProviderKeyReplacementRequest,
        use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)],
    ) -> ProviderKeyResponse:
        command = ReplaceProviderKeyCommand(provider, request.key, request.expires_on)
        return ProviderKeyResponse.of(use_cases.replace_provider_key.execute(command))

    @router.put("/{provider}/expiry", status_code=status.HTTP_204_NO_CONTENT)
    def set_key_expiry(
        provider: str, request: KeyExpiryRequest, use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)]
    ) -> None:
        """The day the user says the key stops working, only when no gateway reads it (R6.2.2)."""
        use_cases.set_provider_key_expiry.execute(SetProviderKeyExpiryCommand(provider, request.expires_on))

    @router.delete("/{provider}", status_code=status.HTTP_204_NO_CONTENT)
    def remove_provider_key(provider: str, use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)]) -> None:
        use_cases.remove_provider_key.execute(RemoveProviderKeyCommand(provider))

    return router
