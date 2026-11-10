from autotrading.domain.errors import DomainError


class AccountNameRequiredError(DomainError):
    def __init__(self) -> None:
        super().__init__("nome obbligatorio")


class ExchangeRequiredError(DomainError):
    def __init__(self) -> None:
        super().__init__("exchange obbligatorio")


class CredentialsRequiredError(DomainError):
    def __init__(self) -> None:
        super().__init__("credenziali obbligatorio")
