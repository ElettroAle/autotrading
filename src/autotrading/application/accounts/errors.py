from collections.abc import Iterable

from autotrading.application.errors import ApplicationError
from autotrading.domain.accounts.account_name import AccountName
from autotrading.domain.accounts.exchange_name import ExchangeName


class UnsupportedExchangeError(ApplicationError):
    def __init__(self, exchange: ExchangeName, supported: Iterable[str]) -> None:
        super().__init__("exchange non supportato")
        self.exchange = exchange
        self.supported = tuple(sorted(supported))


class AccountNameInUseError(ApplicationError):
    def __init__(self, name: AccountName) -> None:
        super().__init__("nome del conto già in uso")
        self.name = name


class ExchangeRejectedCredentialsError(ApplicationError):
    def __init__(self, exchange_message: str) -> None:
        super().__init__("credenziali rifiutate dall'exchange")
        self.exchange_message = exchange_message


class ExchangeUnavailableError(ApplicationError):
    def __init__(self) -> None:
        super().__init__("exchange non raggiungibile, riprovare")
