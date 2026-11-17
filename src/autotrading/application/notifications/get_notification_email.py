from dataclasses import dataclass

from autotrading.application.notifications.ports import MailServerRepositoryPort, NotificationEmailRepositoryPort
from autotrading.domain.notifications.email_address import EmailAddress

MAIL_SERVER_MISSING = "le email non partono: server di posta non configurato"


@dataclass(frozen=True, slots=True)
class NotificationEmailSettings:
    """The address of the notifications by email, if any, and the warning that no email leaves, if so."""

    address: EmailAddress | None
    warning: str | None


class GetNotificationEmailUseCase:
    """The address of the notifications by email of the tenant; without a mail server it can still be indicated, and
    the settings warn that no email leaves (R3.5.2, R3.5.5).
    """

    def __init__(self, emails: NotificationEmailRepositoryPort, servers: MailServerRepositoryPort) -> None:
        self._emails = emails
        self._servers = servers

    def execute(self) -> NotificationEmailSettings:
        email = self._emails.get()
        address = None if email is None else email.address
        warning = None if self._servers.get() is not None else MAIL_SERVER_MISSING
        return NotificationEmailSettings(address, warning)
