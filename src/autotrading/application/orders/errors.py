from collections.abc import Iterable

from autotrading.application.errors import ApplicationError


class OrderAccountNotFoundError(ApplicationError):
    """The same answer for an account that does not exist and for one of another tenant (R0.1.3)."""

    def __init__(self) -> None:
        super().__init__("non trovato")


class UnsupportedOrderExchangeError(ApplicationError):
    def __init__(self, exchange: str, supported: Iterable[str]) -> None:
        super().__init__("exchange non supportato")
        self.exchange = exchange
        self.supported = tuple(sorted(supported))


class ExchangeRejectedOrderError(ApplicationError):
    """The exchange refused the order, or the leverage it needs; the message is the original one, redacted."""

    def __init__(self, exchange_message: str) -> None:
        super().__init__("ordine rifiutato dall'exchange")
        self.exchange_message = exchange_message


class OrderNotAcknowledgedError(ApplicationError):
    """The exchange did not confirm the order in time: it may or may not have been executed."""

    def __init__(self) -> None:
        super().__init__("nessuna conferma dell'exchange all'invio dell'ordine")


class OrderExchangeUnavailableError(ApplicationError):
    def __init__(self) -> None:
        super().__init__("exchange non raggiungibile, riprovare")
