import logging
from collections.abc import Callable, Mapping

from autotrading.application.notifications.errors import MessageNotDeliveredError, UnknownOutboxIntegrationError
from autotrading.application.notifications.ports import MessengerPort
from autotrading.domain.notifications.outbox_message import CHAT_MESSAGE, OutboxMessage

operations = logging.getLogger("autotrading.notifications")


class DeliverOutboxMessageUseCase:
    """Delivers a queued message with the port of its integration (ADR
    outbox-delle-integrazioni-esterne-con-procrastinate).

    A transient error of the port is recorded and raised, for the outbox to retry; a message no port can deliver
    fails with a permanent error, never retried.
    """

    def __init__(self, messenger: MessengerPort) -> None:
        self._messenger = messenger
        self._deliveries: Mapping[str, Callable[[OutboxMessage], None]] = {CHAT_MESSAGE: self._send_to_chat}

    def execute(self, message: OutboxMessage) -> None:
        delivery = self._deliveries.get(message.integration)
        if delivery is None:
            raise UnknownOutboxIntegrationError(message.integration)
        delivery(message)

    def _send_to_chat(self, message: OutboxMessage) -> None:
        chat_message = message.chat_message()
        try:
            self._messenger.send(chat_message.chat_id, chat_message.text)
        except MessageNotDeliveredError:
            operations.warning(
                "invio della notifica fallito",
                exc_info=True,
                extra={"tenant_id": str(message.tenant_id.value), "message_id": str(message.id.value)},
            )
            raise
