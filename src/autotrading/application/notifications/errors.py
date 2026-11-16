from collections.abc import Mapping
from typing import ClassVar

from autotrading.application.errors import ApplicationError


class ChatNotLinkedError(ApplicationError):
    status_code = 404

    def __init__(self) -> None:
        super().__init__("nessuna chat collegata")


class NoLinkedChatToTestError(ChatNotLinkedError):
    """A test asked from the dashboard has no chat to reach: the user must link one first (R2.3.6)."""

    status_code = 409


class MessageNotDeliveredError(ApplicationError):
    """The channel did not take the message: the delivery is recorded and retried, the caller goes on (R1.8.2)."""

    status_code = 503
    reason: ClassVar[str] = "messaggio non consegnato alla chat"

    def __init__(self) -> None:
        super().__init__(self.reason)


class EmailNotDeliveredError(MessageNotDeliveredError):
    """The mail service did not take the email: recorded and retried as every notification (R3.5.2)."""

    reason = "email non consegnata"


class NoNotificationEmailToTestError(ApplicationError):
    """A test email has no address to reach: the user must indicate one first (R3.5.2)."""

    status_code = 409

    def __init__(self) -> None:
        super().__init__("nessun indirizzo email per le notifiche")


class MailServiceNotConfiguredError(ApplicationError):
    """The installation has no mail service: the address is kept, but no email leaves (R3.5.2)."""

    status_code = 409

    def __init__(self) -> None:
        super().__init__("servizio di posta non configurato")


class BotUnreachableError(ApplicationError):
    """Telegram did not answer the bot: the next poll tries again."""

    status_code = 503

    def __init__(self) -> None:
        super().__init__("bot non raggiungibile")


class OutboxUnavailableError(ApplicationError):
    """The outbox could not keep or serve the messages: a notification not queued is recorded, never raised."""

    status_code = 503

    def __init__(self) -> None:
        super().__init__("coda dei messaggi in uscita non disponibile")


class UnknownOutboxIntegrationError(ApplicationError):
    """A queued message names an integration no port delivers: no retry can ever deliver it."""

    declared_permanent = True

    def __init__(self, integration: str) -> None:
        super().__init__("integrazione in uscita sconosciuta")
        self._integration = integration

    @property
    def details(self) -> Mapping[str, object]:
        return {"integration": self._integration}
