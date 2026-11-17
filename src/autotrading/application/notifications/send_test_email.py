from autotrading.application.notifications.errors import MailServiceNotConfiguredError, NoNotificationEmailToTestError
from autotrading.application.notifications.ports import MailServicePort, NotificationEmailRepositoryPort, OutboxPort
from autotrading.domain.notifications.notification import Notification
from autotrading.domain.notifications.notification_email import NotificationEmail
from autotrading.domain.notifications.outbox_message import OutboxMessage


class SendTestEmailUseCase:
    """Queues the test email to the address of the notifications of the tenant, by the road of the real ones
    (R3.5.2, ADR outbox-delle-integrazioni-esterne-con-procrastinate).

    The user asking for a test must know why nothing would arrive: no mail service first, then no address.
    """

    def __init__(
        self, emails: NotificationEmailRepositoryPort, mail_service: MailServicePort, outbox: OutboxPort
    ) -> None:
        self._emails = emails
        self._mail_service = mail_service
        self._outbox = outbox

    def execute(self) -> None:
        email = self._address_to_test()
        test = Notification.test()
        self._outbox.enqueue(OutboxMessage.to_email(email, test.email_subject, test.text))

    def _address_to_test(self) -> NotificationEmail:
        if not self._mail_service.is_configured():
            raise MailServiceNotConfiguredError
        email = self._emails.get()
        if email is None:
            raise NoNotificationEmailToTestError
        return email
