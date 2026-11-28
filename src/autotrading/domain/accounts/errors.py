from collections.abc import Mapping
from decimal import Decimal

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


class DeviationThresholdOutOfRangeError(DomainError):
    """The threshold of the balance deviation of an account goes from a tenth to a hundred percent (R3.3.1)."""

    status_code = 422

    def __init__(self, percent: Decimal) -> None:
        super().__init__("la soglia di scostamento va da 0,1 a 100")
        self.percent = percent

    @property
    def details(self) -> Mapping[str, object]:
        return {"percent": str(self.percent)}


class VirtualBalanceRequiredError(DomainError):
    """An account of an exchange that holds a virtual balance starts from the one the user gives (R6.3.2)."""

    status_code = 422

    def __init__(self) -> None:
        super().__init__("saldo virtuale obbligatorio per questo exchange")


class InvalidVirtualBalanceError(DomainError):
    status_code = 422

    def __init__(self, amount: Decimal) -> None:
        super().__init__("il saldo virtuale deve essere maggiore di zero")
        self.amount = amount

    @property
    def details(self) -> Mapping[str, object]:
        return {"amount": str(self.amount)}


class MaxDirectionExposureNotPositiveError(DomainError):
    """The exposure of the flows of an account on one side is limited to a finite percent of its balance above zero
    (R5.5.5, ADR esposizione-massima-per-direzione-del-conto)."""

    status_code = 422

    def __init__(self, percent: Decimal) -> None:
        super().__init__("l'esposizione massima per direzione è maggiore di 0")
        self.percent = percent

    @property
    def details(self) -> Mapping[str, object]:
        return {"percent": str(self.percent)}


class ReconciliationIntervalOutOfRangeError(DomainError):
    """The periodic check reconciles an account every one to 1440 minutes (Bug 778, ADR
    intervallo-di-riconciliazione-del-conto)."""

    status_code = 422

    def __init__(self, minutes: int) -> None:
        super().__init__("intervallo di riconciliazione da 1 a 1440 minuti")
        self.minutes = minutes

    @property
    def details(self) -> Mapping[str, object]:
        return {"minutes": self.minutes}
