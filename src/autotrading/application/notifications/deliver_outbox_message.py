import logging
from collections.abc import Callable, Mapping

from autotrading.application.notifications.errors import MessageNotDeliveredError, UnknownOutboxIntegrationError
from autotrading.application.notifications.ports import MailerPort, MessengerPort
from autotrading.domain.notifications.outbox_message import CHAT_MESSAGE, EMAIL_MESSAGE, OutboxMessage

operations = logging.getLogger("autotrading.notifications")


class DeliverOutboxMessageUseCase:
    """Delivers a queued message with the port of its integration (ADR
    outbox-delle-integrazioni-esterne-con-procrastinate).

    A transient error of the port is recorded and raised, for the outbox to retry; a message no port can deliver
    fails with a permanent error, never retried.
    """

    def __init__(self, messenger: MessengerPort, mailer: MailerPort) -> None:
        self._messenger = messenger
        self._mailer = mailer
        self._deliveries: Mapping[str, Callable[[OutboxMessage], None]] = {
            CHAT_MESSAGE: self._send_to_chat,
            EMAIL_MESSAGE: self._send_email,
        }

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
            _record_failure("invio della notifica fallito", message)
            raise

    def _send_email(self, message: OutboxMessage) -> None:
        email = message.email_message()
        try:
            self._mailer.send(email.address, email.subject, email.text)
        except MessageNotDeliveredError:
            _record_failure("invio dell'email fallito", message)
            raise


def _record_failure(event: str, message: OutboxMessage) -> None:
    operations.warning(
        event,
        exc_info=True,
        extra={"tenant_id": str(message.tenant_id.value), "message_id": str(message.id.value)},
    )
