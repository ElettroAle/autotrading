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
from autotrading.domain.notifications.notification_channel import Channels, NotificationChannel, in_order
from autotrading.domain.notifications.outbox_message import OutboxMessage

operations = logging.getLogger("autotrading.notifications")


class NotifyUseCase:
    """Queues a notification for the channels of the tenant, and for nobody else: the linked chat (R1.8.2) and the
    address of the notifications by email when the tenant has a mail server (R3.5.2, R3.5.5), each only when it is
    among the channels chosen for the type of event, or for the exception of its flow (R3.5.3, ADR
    canali-delle-notifiche-come-insieme).

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
        channels = self._channels_of(notification)
        for message in self._messages_of(notification, channels):
            self._enqueue(message, notification)

    def _channels_of(self, notification: Notification) -> Channels:
        # The test notification is no event: it reaches every channel the tenant linked.
        if notification.event is None:
            return frozenset(NotificationChannel)
        return self._choices.preferences.get().channels_for(notification.event, self._flow_id_of(notification))

    def _flow_id_of(self, notification: Notification) -> UUID | None:
        """The flow the notification names, by its name among the flows not archived; none for the account."""
        if notification.flow is None:
            return None
        return next((flow.flow_id for flow in self._choices.flows.list() if flow.name == notification.flow), None)

    def _messages_of(self, notification: Notification, channels: Channels) -> list[OutboxMessage]:
        """One message for each chosen channel the tenant can be reached on, in the order of the channels."""
        messages = (self._message_on(channel, notification) for channel in in_order(channels))
        return [message for message in messages if message is not None]

    def _message_on(self, channel: NotificationChannel, notification: Notification) -> OutboxMessage | None:
        # A channel is one entry here: a new one adds its message, never a combination of the others.
        messages_by_channel = {
            NotificationChannel.TELEGRAM: self._chat_message,
            NotificationChannel.EMAIL: self._email_message,
        }
        return messages_by_channel[channel](notification)

    def _chat_message(self, notification: Notification) -> OutboxMessage | None:
        chat = self._chats.get()
        return None if chat is None else OutboxMessage.to_chat(chat, notification.text)

    def _email_message(self, notification: Notification) -> OutboxMessage | None:
        email = self._emails.get()
        if email is None or self._mail_servers.get() is None:
            return None
        return OutboxMessage.to_email(email, notification.title, notification.text)

    def _enqueue(self, message: OutboxMessage, notification: Notification) -> None:
        try:
            self._outbox.enqueue(message)
        except OutboxUnavailableError:
            operations.warning(
                "notifica non accodata",
                exc_info=True,
                extra={"tenant_id": str(message.tenant_id.value), "subject": notification.subject},
            )
