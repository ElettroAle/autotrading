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
