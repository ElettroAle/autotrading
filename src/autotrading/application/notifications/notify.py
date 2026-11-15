import logging

from autotrading.application.notifications.errors import OutboxUnavailableError
from autotrading.application.notifications.ports import LinkedChatRepositoryPort, OutboxPort
from autotrading.domain.notifications.notification import Notification
from autotrading.domain.notifications.outbox_message import OutboxMessage

operations = logging.getLogger("autotrading.notifications")


class NotifyUseCase:
    """Queues a notification for the chat linked to the tenant, and for nobody else (R1.8.2).

    Without a linked chat nothing is queued; the outbox delivers it and retries a failed sending (ADR
    outbox-delle-integrazioni-esterne-con-procrastinate). A notification not queued is recorded and never fails the
    caller.
    """

    def __init__(self, chats: LinkedChatRepositoryPort, outbox: OutboxPort) -> None:
        self._chats = chats
        self._outbox = outbox

    def execute(self, notification: Notification) -> None:
        chat = self._chats.get()
        if chat is None:
            return
        try:
            self._outbox.enqueue(OutboxMessage.to_chat(chat, notification.text))
        except OutboxUnavailableError:
            operations.warning(
                "notifica non accodata",
                exc_info=True,
                extra={"tenant_id": str(chat.tenant_id.value), "subject": notification.subject},
            )
