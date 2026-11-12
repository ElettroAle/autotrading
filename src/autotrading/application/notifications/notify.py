import logging

from autotrading.application.notifications.errors import MessageNotDeliveredError
from autotrading.application.notifications.ports import LinkedChatRepositoryPort, MessengerPort
from autotrading.domain.notifications.notification import Notification

operations = logging.getLogger("autotrading.notifications")


class NotifyUseCase:
    """Sends a notification to the chat linked to the tenant, and to nobody else (R1.8.2).

    Without a linked chat nothing is sent; a failed sending is recorded and never fails the caller.
    """

    def __init__(self, chats: LinkedChatRepositoryPort, messenger: MessengerPort) -> None:
        self._chats = chats
        self._messenger = messenger

    def execute(self, notification: Notification) -> None:
        chat = self._chats.get()
        if chat is None:
            return
        try:
            self._messenger.send(chat.chat_id, notification.text)
        except MessageNotDeliveredError:
            operations.warning(
                "invio della notifica fallito",
                exc_info=True,
                extra={"tenant_id": str(chat.tenant_id.value), "subject": notification.subject},
            )
