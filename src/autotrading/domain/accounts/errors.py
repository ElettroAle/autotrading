from collections.abc import Mapping

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


class CredentialFieldRequiredError(DomainError):
    status_code = 422

    def __init__(self, field: str, label: str) -> None:
        # Only the first letter changes: the label may hold a name, as in "chiave dell'API wallet".
        super().__init__(f"{label[:1].lower()}{label[1:]} obbligatorio")
        self.field = field

    @property
    def details(self) -> Mapping[str, object]:
        return {"field": self.field}


class UnknownCredentialFieldError(DomainError):
    status_code = 422

    def __init__(self, field: str) -> None:
        super().__init__(f"campo delle credenziali non previsto: {field}")
        self.field = field

    @property
    def details(self) -> Mapping[str, object]:
        return {"field": self.field}


class PublicCredentialFieldNotReplaceableError(DomainError):
    """A public field names the account on the exchange: another value is another account (R0.2.4, Bug 401)."""

    def __init__(self, field: str, label: str) -> None:
        # Only the first letter changes: the label may hold a name, as in "chiave dell'API wallet".
        super().__init__(
            f"{label[:1].lower()}{label[1:]} non si sostituisce: per cambiarlo rimuovi il conto e registrane uno nuovo"
        )
        self.field = field

    @property
    def details(self) -> Mapping[str, object]:
        return {"field": self.field}


class CredentialsOfAnotherAccountError(DomainError):
    status_code = 422

    def __init__(self) -> None:
        super().__init__("le credenziali appartengono a un altro conto dell'exchange")


class UndeclaredEnvironmentError(DomainError):
    def __init__(self) -> None:
        super().__init__("ambiente non dichiarato")


class UnsupportedEnvironmentError(DomainError):
    def __init__(self, environment: str, supported: tuple[str, ...]) -> None:
        super().__init__("ambiente non ammesso: sono ammessi " + " e ".join(supported))
        self.environment = environment
