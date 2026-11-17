from collections.abc import Mapping

from autotrading.domain.errors import DomainError


class InvalidNotificationError(DomainError):
    """A notification without the flow or account it names: a defect of the caller, never of the user."""

    def __init__(self) -> None:
        super().__init__("notifica senza flusso o conto")


class InvalidNotificationTargetError(DomainError):
    """A position a notification leads to without the asset, or the instant it closed, that finds it: a defect of the
    caller, never of the user (R3.5.6).
    """

    def __init__(self) -> None:
        super().__init__("destinazione della notifica senza la posizione")


class InvalidOutboxMessageError(DomainError):
    """A queued message that does not carry what its integration needs: no retry can ever deliver it."""

    declared_permanent = True

    def __init__(self) -> None:
        super().__init__("messaggio in uscita senza chat o testo")


class AccountEventWithoutFlowExceptionError(DomainError):
    """An event of the account belongs to no single flow: it follows the general choice only (R3.5.3)."""

    def __init__(self, event: str) -> None:
        super().__init__(f"{event} è un evento del conto: segue la scelta generale")
        self._event = event

    @property
    def details(self) -> Mapping[str, object]:
        return {"event": self._event}


class InvalidEmailAddressError(DomainError):
    """An address without the form of an email: the user writes it again."""

    def __init__(self, address: str) -> None:
        super().__init__("indirizzo email non valido")
        self.address = address

    @property
    def details(self) -> Mapping[str, object]:
        return {"address": self.address}


class InvalidMailServerHostError(DomainError):
    """A mail server without the form of a host name: the user writes it again (R3.5.5)."""

    def __init__(self, host: str) -> None:
        super().__init__("server di posta non valido")
        self.host = host

    @property
    def details(self) -> Mapping[str, object]:
        return {"host": self.host}


class InvalidMailServerPortError(DomainError):
    def __init__(self, port: int) -> None:
        super().__init__("porta del server di posta non valida: da 1 a 65535")
        self.port = port

    @property
    def details(self) -> Mapping[str, object]:
        return {"port": self.port}


class InvalidMailServerUsernameError(DomainError):
    def __init__(self, username: str) -> None:
        super().__init__("utente del server di posta mancante")
        self.username = username

    @property
    def details(self) -> Mapping[str, object]:
        return {"username": self.username}


class InvalidMailSenderError(DomainError):
    """The sender, or the user standing for it, has not the form of an email: no server would send as it (R3.5.5)."""

    def __init__(self, sender: str) -> None:
        super().__init__("mittente non valido")
        self.sender = sender

    @property
    def details(self) -> Mapping[str, object]:
        return {"sender": self.sender}
