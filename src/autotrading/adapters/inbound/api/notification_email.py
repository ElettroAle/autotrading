from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from autotrading.adapters.inbound.api.tenant_use_cases import TenantUseCases
from autotrading.application.notifications.get_notification_email import NotificationEmailSettings
from autotrading.application.notifications.set_notification_email import SetNotificationEmailCommand


class NotificationEmailRequest(BaseModel):
    """The address the notifications go to by email; the platform checks its form (R3.5.2)."""

    address: str


class NotificationEmailResponse(BaseModel):
    """The address of the notifications by email, if any, and the warning that no email leaves when the
    installation has no mail service (R3.5.2)."""

    address: str | None
    warning: str | None

    @classmethod
    def of(cls, settings: NotificationEmailSettings) -> NotificationEmailResponse:
        address = None if settings.address is None else settings.address.value
        return cls(address=address, warning=settings.warning)


def notification_email_router(use_cases_of_request: Callable[..., TenantUseCases]) -> APIRouter:
    router = APIRouter(prefix="/notifications/email", tags=["notifiche email"])

    @router.get("")
    def read_notification_email(
        use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)],
    ) -> NotificationEmailResponse:
        return NotificationEmailResponse.of(use_cases.get_notification_email.execute())

    @router.put("", status_code=status.HTTP_204_NO_CONTENT)
    def set_notification_email(
        request: NotificationEmailRequest, use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)]
    ) -> None:
        use_cases.set_notification_email.execute(SetNotificationEmailCommand(request.address))

    @router.delete("", status_code=status.HTTP_204_NO_CONTENT)
    def remove_notification_email(use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)]) -> None:
        use_cases.remove_notification_email.execute()

    @router.post("/test", status_code=status.HTTP_202_ACCEPTED)
    def send_test_email(use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)]) -> None:
        use_cases.send_test_email.execute()

    return router
