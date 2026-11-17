from collections.abc import Mapping

from autotrading.domain.errors import DomainError


class InvalidNotificationError(DomainError):
    """A notification without the flow or account it names: a defect of the caller, never of the user."""

    def __init__(self) -> None:
        super().__init__("notifica senza flusso o conto")


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
