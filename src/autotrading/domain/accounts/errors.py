from autotrading.domain.errors import DomainError


class AccountNameRequiredError(DomainError):
    status_code = 422

    def __init__(self) -> None:
        super().__init__("nome obbligatorio")


class ExchangeRequiredError(DomainError):
    status_code = 422

    def __init__(self) -> None:
        super().__init__("exchange obbligatorio")


class CredentialsRequiredError(DomainError):
    status_code = 422

    def __init__(self) -> None:
        super().__init__("credenziali obbligatorio")


class CredentialsOfAnotherAccountError(DomainError):
    status_code = 422

    def __init__(self) -> None:
        super().__init__("le credenziali appartengono a un altro conto dell'exchange")


class OpenPositionsNeedConfirmationError(DomainError):
    status_code = 409

    def __init__(self) -> None:
        super().__init__("il conto ha posizioni aperte che resteranno sull'exchange senza gestione")
