from collections.abc import Iterable, Mapping

from autotrading.application.errors import ApplicationError
from autotrading.domain.accounts.account_name import AccountName
from autotrading.domain.accounts.exchange_name import ExchangeName


class UnsupportedExchangeError(ApplicationError):
    status_code = 422

    def __init__(self, exchange: ExchangeName, supported: Iterable[str]) -> None:
        super().__init__("exchange non supportato")
        self.exchange = exchange
        self.supported = tuple(sorted(supported))

    @property
    def details(self) -> Mapping[str, object]:
        return {"supported": list(self.supported)}


class AccountNameInUseError(ApplicationError):
    status_code = 409

    def __init__(self, name: AccountName) -> None:
        super().__init__("nome del conto già in uso")
        self.name = name


class ExchangeRejectedCredentialsError(ApplicationError):
    status_code = 422

    def __init__(self, exchange_message: str) -> None:
        super().__init__("credenziali rifiutate dall'exchange")
        self.exchange_message = exchange_message

    @property
    def details(self) -> Mapping[str, object]:
        return {"exchange_message": self.exchange_message}


class ExchangeUnavailableError(ApplicationError):
    status_code = 503

    def __init__(self) -> None:
        super().__init__("exchange non raggiungibile, riprovare")


class AccountNotFoundError(ApplicationError):
    """The same answer for an account that does not exist and for one of another tenant (R0.1.3)."""

    status_code = 404

    def __init__(self) -> None:
        super().__init__("non trovato")


class CredentialsNotOpenedError(ApplicationError):
    """The sealed credentials do not belong to the account asked for, or no key of the installation opens them."""

    status_code = 500

    def __init__(self) -> None:
        super().__init__("credenziali del conto non leggibili")


class WorkerUnavailableError(ApplicationError):
    status_code = 503

    def __init__(self) -> None:
        super().__init__("servizio di esecuzione non raggiungibile, riprovare")
