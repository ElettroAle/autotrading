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


class MailServerRefusedLoginError(EmailNotDeliveredError):
    """The mail server of the tenant refused its user and password: only the user can correct them (R3.5.5)."""

    status_code = 400
    reason = "il server di posta ha rifiutato l'accesso: controlla utente e password"


class MailServerNotConfiguredError(ApplicationError):
    """The tenant has no mail server: the address is kept, but no email leaves (R3.5.5)."""

    status_code = 409

    def __init__(self) -> None:
        super().__init__("server di posta non configurato")


class MailPasswordRequiredError(ApplicationError):
    """A mail server saved for the first time has no password to keep: a change without one keeps the saved one."""

    def __init__(self) -> None:
        super().__init__("password del server di posta mancante")


class MailPasswordNotOpenedError(ApplicationError):
    """The sealed password is not one sealed for this tenant, or the key that sealed it is gone: the user saves it
    again (ADR server-di-posta-per-tenant)."""

    status_code = 409

    def __init__(self) -> None:
        super().__init__("password del server di posta non leggibile: salvala di nuovo")


class NotifiedFlowNotFoundError(ApplicationError):
    """The same answer for a flow that does not exist and for one of another tenant (R0.1.3)."""

    status_code = 404

    def __init__(self) -> None:
        super().__init__("flusso non trovato")


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


class FlowStatusUnavailableError(ApplicationError):
    """The state of the flow could not be read: the notification leaves without it, and the failure is recorded (ADR
    stato-del-flusso-in-ogni-notifica).
    """

    status_code = 503

    def __init__(self) -> None:
        super().__init__("stato del flusso non disponibile")


class UnknownOutboxIntegrationError(ApplicationError):
    """A queued message names an integration no port delivers: no retry can ever deliver it."""

    declared_permanent = True

    def __init__(self, integration: str) -> None:
        super().__init__("integrazione in uscita sconosciuta")
        self._integration = integration

    @property
    def details(self) -> Mapping[str, object]:
        return {"integration": self._integration}


class AlertNotFoundError(ApplicationError):
    """The same answer for an alert that does not exist and for one of another tenant (R0.1.3)."""

    status_code = 404

    def __init__(self) -> None:
        super().__init__("avviso non trovato")


class AlertCursorInvalidError(ApplicationError):
    """The cursor of a page of alerts is not one the list gave: the user starts again from the first page."""

    def __init__(self) -> None:
        super().__init__("cursore degli avvisi non valido")


class NotificationInboxUnavailableError(ApplicationError):
    """The bell could not keep the notification: recorded, never raised, and the channels get their messages (ADR
    notifiche-nell-app-salvate-per-tenant)."""

    status_code = 503

    def __init__(self) -> None:
        super().__init__("notifiche del campanello non disponibili")


class InboxNotificationNotFoundError(ApplicationError):
    """The same answer for a notification that does not exist and for one of another tenant (R0.1.3)."""

    status_code = 404

    def __init__(self) -> None:
        super().__init__("notifica non trovata")


class InboxCursorInvalidError(ApplicationError):
    """The cursor of a page of the bell is not one the list gave: the user starts again from the first page."""

    def __init__(self) -> None:
        super().__init__("cursore delle notifiche non valido")
