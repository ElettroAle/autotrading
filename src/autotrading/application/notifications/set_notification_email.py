from dataclasses import dataclass

from autotrading.application.notifications.ports import NotificationEmailRepositoryPort
from autotrading.domain.notifications.email_address import EmailAddress
from autotrading.domain.notifications.notification_email import NotificationEmail
from autotrading.domain.tenancy.tenant_id import TenantId


@dataclass(frozen=True, slots=True)
class SetNotificationEmailCommand:
    address: str


class SetNotificationEmailUseCase:
    """Keeps the address the notifications of the tenant go to by email: it counts at once, without a verification,
    and replaces the one kept before (R3.5.2).
    """

    def __init__(self, tenant_id: TenantId, emails: NotificationEmailRepositoryPort) -> None:
        self._tenant_id = tenant_id
        self._emails = emails

    def execute(self, command: SetNotificationEmailCommand) -> None:
        address = EmailAddress.parse(command.address)
        self._emails.set(NotificationEmail(self._tenant_id, address))
