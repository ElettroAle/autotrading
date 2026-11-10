from autotrading.domain.errors import DomainError


class EmptyUserIdError(DomainError):
    def __init__(self) -> None:
        super().__init__("identificativo utente vuoto")
