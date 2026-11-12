from autotrading.domain.errors import DomainError


class InvalidNotificationError(DomainError):
    """A notification without the flow or account it names: a defect of the caller, never of the user."""

    def __init__(self) -> None:
        super().__init__("notifica senza flusso o conto")
