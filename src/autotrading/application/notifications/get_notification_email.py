from dataclasses import dataclass

from autotrading.application.notifications.ports import MailServicePort, NotificationEmailRepositoryPort
from autotrading.domain.notifications.email_address import EmailAddress

MAIL_SERVICE_MISSING = "le email non partono: servizio di posta non configurato"


@dataclass(frozen=True, slots=True)
class NotificationEmailSettings:
    """The address of the notifications by email, if any, and the warning that no email leaves, if so."""

    address: EmailAddress | None
    warning: str | None


class GetNotificationEmailUseCase:
    """The address of the notifications by email of the tenant; without a mail service it can still be indicated,
    and the settings warn that no email leaves (R3.5.2).
    """

    def __init__(self, emails: NotificationEmailRepositoryPort, mail_service: MailServicePort) -> None:
        self._emails = emails
        self._mail_service = mail_service

    def execute(self) -> NotificationEmailSettings:
        email = self._emails.get()
        address = None if email is None else email.address
        warning = None if self._mail_service.is_configured() else MAIL_SERVICE_MISSING
        return NotificationEmailSettings(address, warning)
