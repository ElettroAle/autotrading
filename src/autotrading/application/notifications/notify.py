import logging
from uuid import UUID

from autotrading.application.notifications.errors import OutboxUnavailableError
from autotrading.application.notifications.ports import (
    ChannelChoicePorts,
    LinkedChatRepositoryPort,
    MailServerRepositoryPort,
    NotificationEmailRepositoryPort,
    OutboxPort,
)
from autotrading.domain.notifications.notification import Notification
from autotrading.domain.notifications.notification_channel import NotificationChannel
from autotrading.domain.notifications.outbox_message import OutboxMessage

operations = logging.getLogger("autotrading.notifications")


class NotifyUseCase:
    """Queues a notification for the channels of the tenant, and for nobody else: the linked chat (R1.8.2) and the
    address of the notifications by email when the tenant has a mail server (R3.5.2, R3.5.5), each only when the
    channel chosen for the type of event, or the exception of its flow, reaches it (R3.5.3).

    Without a channel nothing is queued; the outbox delivers each message and retries a failed sending (ADR
    outbox-delle-integrazioni-esterne-con-procrastinate). A message not queued is recorded and never fails the
    caller, nor keeps the other channel from its message.
    """

    def __init__(
        self,
        chats: LinkedChatRepositoryPort,
        emails: NotificationEmailRepositoryPort,
        mail_servers: MailServerRepositoryPort,
        outbox: OutboxPort,
        choices: ChannelChoicePorts,
    ) -> None:
        self._chats = chats
        self._emails = emails
        self._mail_servers = mail_servers
        self._outbox = outbox
        self._choices = choices

    def execute(self, notification: Notification) -> None:
        channel = self._channel_of(notification)
        for message in self._messages_of(notification, channel):
            self._enqueue(message, notification)

    def _channel_of(self, notification: Notification) -> NotificationChannel:
        # The test notification is no event: it reaches every channel the tenant linked.
        if notification.event is None:
            return NotificationChannel.BOTH
        return self._choices.preferences.get().channel_for(notification.event, self._flow_id_of(notification))

    def _flow_id_of(self, notification: Notification) -> UUID | None:
        """The flow the notification names, by its name among the flows not archived; none for the account."""
        if notification.flow is None:
            return None
        return next((flow.flow_id for flow in self._choices.flows.list() if flow.name == notification.flow), None)

    def _messages_of(self, notification: Notification, channel: NotificationChannel) -> list[OutboxMessage]:
        messages = []
        chat = self._chats.get() if channel.reaches_chat else None
        if chat is not None:
            messages.append(OutboxMessage.to_chat(chat, notification.text))
        email = self._emails.get() if channel.reaches_email else None
        if email is not None and self._mail_servers.get() is not None:
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
