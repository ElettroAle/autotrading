from collections.abc import Mapping

from autotrading.application.errors import ApplicationError


class ChatNotLinkedError(ApplicationError):
    status_code = 404

    def __init__(self) -> None:
        super().__init__("nessuna chat collegata")


class NoLinkedChatToTestError(ChatNotLinkedError):
    """A test asked from the dashboard has no chat to reach: the user must link one first (R2.3.6)."""

    status_code = 409


class MessageNotDeliveredError(ApplicationError):
    """Telegram did not take the message: the notification is lost and recorded, the caller goes on (R1.8.2)."""

    status_code = 503

    def __init__(self) -> None:
        super().__init__("messaggio non consegnato alla chat")


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

    permanent = True

    def __init__(self, integration: str) -> None:
        super().__init__("integrazione in uscita sconosciuta")
        self._integration = integration

    @property
    def details(self) -> Mapping[str, object]:
        return {"integration": self._integration}
