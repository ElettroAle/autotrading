from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from autotrading.adapters.inbound.api.tenant_use_cases import TenantUseCases
from autotrading.application.notifications.get_mail_server import MailServerSettings
from autotrading.application.notifications.set_mail_server import SetMailServerCommand
from autotrading.domain.notifications.mail_security import MailSecurity


class MailServerRequest(BaseModel):
    """The mail server the emails of the user leave from; a password left out keeps the saved one (R3.5.5)."""

    host: str
    port: int
    security: MailSecurity
    username: str
    sender: str = ""
    password: str | None = Field(default=None, repr=False)

    def command(self) -> SetMailServerCommand:
        return SetMailServerCommand(self.host, self.port, self.security, self.username, self.sender, self.password)


class MailServerResponse(BaseModel):
    """The mail server of the user: never its password, only that one is saved (ADR server-di-posta-per-tenant)."""

    host: str
    port: int
    security: MailSecurity
    username: str
    sender: str
    password_saved: bool

    @classmethod
    def of(cls, settings: MailServerSettings) -> MailServerResponse:
        return cls(
            host=settings.host,
            port=settings.port,
            security=settings.security,
            username=settings.username,
            sender=settings.sender,
            password_saved=settings.password_saved,
        )


def mail_server_router(use_cases_of_request: Callable[..., TenantUseCases]) -> APIRouter:
    router = APIRouter(prefix="/notifications/mail-server", tags=["notifiche email"])

    @router.get("")
    def read_mail_server(
        use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)],
    ) -> MailServerResponse | None:
        settings = use_cases.get_mail_server.execute()
        return None if settings is None else MailServerResponse.of(settings)

    @router.put("", status_code=status.HTTP_204_NO_CONTENT)
    def set_mail_server(
        request: MailServerRequest, use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)]
    ) -> None:
        use_cases.set_mail_server.execute(request.command())

    @router.delete("", status_code=status.HTTP_204_NO_CONTENT)
    def remove_mail_server(use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)]) -> None:
        use_cases.remove_mail_server.execute()

    return router
