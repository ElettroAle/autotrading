import logging

from autotrading.application.notifications.errors import OutboxUnavailableError
from autotrading.application.notifications.ports import (
    LinkedChatRepositoryPort,
    MailServicePort,
    NotificationEmailRepositoryPort,
    OutboxPort,
)
from autotrading.domain.notifications.notification import Notification
from autotrading.domain.notifications.outbox_message import OutboxMessage

operations = logging.getLogger("autotrading.notifications")


class NotifyUseCase:
    """Queues a notification for the channels of the tenant, and for nobody else: the linked chat (R1.8.2) and the
    address of the notifications by email when the installation has a mail service (R3.5.2).

    Without a channel nothing is queued; the outbox delivers each message and retries a failed sending (ADR
    outbox-delle-integrazioni-esterne-con-procrastinate). A message not queued is recorded and never fails the
    caller, nor keeps the other channel from its message.
    """

    def __init__(
        self,
        chats: LinkedChatRepositoryPort,
        emails: NotificationEmailRepositoryPort,
        mail_service: MailServicePort,
        outbox: OutboxPort,
    ) -> None:
        self._chats = chats
        self._emails = emails
        self._mail_service = mail_service
        self._outbox = outbox

    def execute(self, notification: Notification) -> None:
        for message in self._messages_of(notification):
            self._enqueue(message, notification)

    def _messages_of(self, notification: Notification) -> list[OutboxMessage]:
        # Until R3.5.3 every notification goes to every channel the tenant has.
        messages = []
        chat = self._chats.get()
        if chat is not None:
            messages.append(OutboxMessage.to_chat(chat, notification.text))
        email = self._emails.get()
        if email is not None and self._mail_service.is_configured():
            messages.append(OutboxMessage.to_email(email, notification.title, notification.text))
        return messages

    def _enqueue(self, message: OutboxMessage, notification: Notification) -> None:
        try:
            self._outbox.enqueue(message)
        except OutboxUnavailableError:
            operations.warning(
                "notifica non accodata",
                exc_info=True,
                extra={"tenant_id": str(message.tenant_id.value), "subject": notification.subject},
            )
