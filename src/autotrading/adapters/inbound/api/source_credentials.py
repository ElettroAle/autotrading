from collections.abc import Callable
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from autotrading.adapters.inbound.api.key_expiry import ExpiryStatus, KeyExpiryRequest, KeyExpiryResponse
from autotrading.adapters.inbound.api.sources import SourceConfigurationFieldResponse
from autotrading.adapters.inbound.api.tenant_use_cases import TenantUseCases
from autotrading.application.sources.configure_source_adapter import ConfigureSourceAdapterCommand
from autotrading.application.sources.remove_source_credentials import RemoveSourceCredentialsCommand
from autotrading.application.sources.set_source_credentials_expiry import SetSourceCredentialsExpiryCommand
from autotrading.application.sources.source_credentials_summary import SourceCredentialsSummary


class SourceCredentialsRequest(BaseModel):
    # The values of the fields the adapter declares, by name: the domain checks them and seals the secret ones.
    values: dict[str, str] = Field(default_factory=dict)
    # The day the credentials stop working, when the user knows it (R6.2.2).
    expires_on: date | None = None

    def __repr_args__(self) -> list[tuple[str | None, object]]:
        return []


class SourceCredentialsResponse(BaseModel):
    """An adapter that needs configuration on the page of the keys: the sources it offers, the fields it declares,
    whether the tenant configured it, the values that are not secret and when they were saved, the expiry as of today
    and whether the provider refused the credentials; never a secret (R4.1.2, R6.2.2).
    """

    adapter: str
    sources: list[str]
    configuration_fields: list[SourceConfigurationFieldResponse]
    configured: bool
    public_values: dict[str, str]
    registered_at: str | None
    rejected: bool
    expiry: KeyExpiryResponse | None
    expiry_status: ExpiryStatus
    days_left: int | None
    expiry_editable: bool

    @classmethod
    def of(cls, summary: SourceCredentialsSummary) -> SourceCredentialsResponse:
        expiry, registered_at = summary.expiry, summary.registered_at
        return cls(
            adapter=summary.adapter,
            sources=list(summary.sources),
            configuration_fields=[SourceConfigurationFieldResponse.of(field) for field in summary.fields],
            configured=summary.configured,
            public_values=dict(summary.public_values),
            registered_at=None if registered_at is None else registered_at.isoformat(),
            rejected=summary.rejected,
            expiry=None if expiry is None else KeyExpiryResponse.of(expiry.expires_on, expiry.source),
            expiry_status=ExpiryStatus(summary.reading.status.value),
            days_left=summary.reading.days_left,
            expiry_editable=summary.expiry_editable,
        )


def source_credentials_router(use_cases_of_request: Callable[..., TenantUseCases]) -> APIRouter:
    router = APIRouter(prefix="/source-credentials", tags=["credenziali delle fonti"])

    @router.get("")
    def list_source_credentials(
        use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)],
    ) -> list[SourceCredentialsResponse]:
        return [SourceCredentialsResponse.of(summary) for summary in use_cases.list_source_credentials.execute()]

    @router.put(
        "/{adapter}",
        status_code=status.HTTP_204_NO_CONTENT,
        responses={404: {"description": "adapter non disponibile"}, 422: {"description": "valori non validi"}},
    )
    def configure_source_adapter(
        adapter: str,
        request: SourceCredentialsRequest,
        use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)],
    ) -> None:
        """Saves the credentials of the adapter, or replaces them: the secret values are sealed and never answered."""
        command = ConfigureSourceAdapterCommand(adapter, request.values, request.expires_on)
        use_cases.configure_source_adapter.execute(command)

    @router.put("/{adapter}/expiry", status_code=status.HTTP_204_NO_CONTENT)
    def set_source_credentials_expiry(
        adapter: str, request: KeyExpiryRequest, use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)]
    ) -> None:
        """The day the user says the credentials stop working, none to forget it (R6.2.2)."""
        use_cases.set_source_credentials_expiry.execute(SetSourceCredentialsExpiryCommand(adapter, request.expires_on))

    @router.delete("/{adapter}", status_code=status.HTTP_204_NO_CONTENT)
    def remove_source_credentials(
        adapter: str, use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)]
    ) -> None:
        use_cases.remove_source_credentials.execute(RemoveSourceCredentialsCommand(adapter))

    return router
