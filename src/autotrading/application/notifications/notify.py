import logging

from autotrading.application.notifications.errors import NotificationInboxUnavailableError, OutboxUnavailableError
from autotrading.application.notifications.ports import (
    LinkedChatRepositoryPort,
    MailServerRepositoryPort,
    NotificationEmailRepositoryPort,
    NotificationInbox,
    NotificationRoutes,
    OutboxPort,
)
from autotrading.domain.notifications.notification import Notification
from autotrading.domain.notifications.notification_channel import Channels, NotificationChannel, in_order
from autotrading.domain.notifications.outbox_message import Links, OutboxMessage

operations = logging.getLogger("autotrading.notifications")


class NotifyUseCase:
    """Queues a notification for the channels of the tenant, and for nobody else: the linked chat (R1.8.2) and the
    address of the notifications by email when the tenant has a mail server (R3.5.2, R3.5.5), each only when it is
    among the channels chosen for the type of event, or for the exception of its flow (R3.5.3, ADR
    canali-delle-notifiche-come-insieme). Every message carries the links to the pages of the dashboard the notification
    leads to (ADR destinazioni-delle-notifiche-nella-dashboard).

    Without a channel nothing is queued; the outbox delivers each message and retries a failed sending (ADR
    outbox-delle-integrazioni-esterne-con-procrastinate). A message not queued is recorded and never fails the
    caller, nor keeps the other channel from its message.

    Before any channel, every notification is kept in the bell of the tenant, whatever its channels and their links
    (R6.2.1, ADR notifiche-nell-app-salvate-per-tenant); a bell out of reach is recorded like a message not queued.
    """

    def __init__(  # noqa: PLR0913, PLR0917 - the addresses of the channels, the queue, the routes and the bell of the tenant
        self,
        chats: LinkedChatRepositoryPort,
        emails: NotificationEmailRepositoryPort,
        mail_servers: MailServerRepositoryPort,
        outbox: OutboxPort,
        routes: NotificationRoutes,
        inbox: NotificationInbox,
    ) -> None:
        self._chats = chats
        self._emails = emails
        self._mail_servers = mail_servers
        self._outbox = outbox
        self._routes = routes
        self._inbox = inbox

    def execute(self, notification: Notification) -> None:
        self._keep_in_inbox(notification)
        channels = self._channels_of(notification)
        links = self._links_of(notification)
        for message in self._messages_of(notification, channels, links):
            self._enqueue(message, notification)

    def _keep_in_inbox(self, notification: Notification) -> None:
        try:
            self._inbox.notifications.add(notification, self._inbox.clock.now())
        except NotificationInboxUnavailableError:
            operations.warning(
                "notifica non salvata nel campanello",
                exc_info=True,
                extra={"subject": notification.subject},
            )

    def _channels_of(self, notification: Notification) -> Channels:
        # The test notification is no event: it reaches every channel the tenant linked.
        if notification.event is None:
            return frozenset(NotificationChannel)
        return self._routes.preferences.get().channels_for(notification.event, notification.flow_id)

    def _links_of(self, notification: Notification) -> Links:
        """The pages the notification leads to, in its order; none without a dashboard to lead to."""
        links = (self._routes.links.link(target) for target in notification.targets)
        return tuple(link for link in links if link is not None)

    def _messages_of(self, notification: Notification, channels: Channels, links: Links) -> list[OutboxMessage]:
        """One message for each chosen channel the tenant can be reached on, in the order of the channels."""
        messages = (self._message_on(channel, notification, links) for channel in in_order(channels))
        return [message for message in messages if message is not None]

    def _message_on(
        self, channel: NotificationChannel, notification: Notification, links: Links
    ) -> OutboxMessage | None:
        # A channel is one entry here: a new one adds its message, never a combination of the others.
        messages_by_channel = {
            NotificationChannel.TELEGRAM: self._chat_message,
            NotificationChannel.EMAIL: self._email_message,
        }
        return messages_by_channel[channel](notification, links)

    def _chat_message(self, notification: Notification, links: Links) -> OutboxMessage | None:
        chat = self._chats.get()
        return None if chat is None else OutboxMessage.to_chat(chat, notification.text, links=links)

    def _email_message(self, notification: Notification, links: Links) -> OutboxMessage | None:
        email = self._emails.get()
        if email is None or self._mail_servers.get() is None:
            return None
        return OutboxMessage.to_email(email, notification.title, notification.text, links=links)

    def _enqueue(self, message: OutboxMessage, notification: Notification) -> None:
        try:
            self._outbox.enqueue(message)
        except OutboxUnavailableError:
            operations.warning(
                "notifica non accodata",
                exc_info=True,
                extra={"tenant_id": str(message.tenant_id.value), "subject": notification.subject},
            )
