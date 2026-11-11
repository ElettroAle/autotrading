from collections.abc import Iterable, Mapping

from autotrading.application.errors import ApplicationError


class OrderAccountNotFoundError(ApplicationError):
    """The same answer for an account that does not exist and for one of another tenant (R0.1.3)."""

    status_code = 404

    def __init__(self) -> None:
        super().__init__("non trovato")


class UnsupportedOrderExchangeError(ApplicationError):
    status_code = 422

    def __init__(self, exchange: str, supported: Iterable[str]) -> None:
        super().__init__("exchange non supportato")
        self.exchange = exchange
        self.supported = tuple(sorted(supported))

    @property
    def details(self) -> Mapping[str, object]:
        return {"supported": list(self.supported)}


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
    status_code = 503

    def __init__(self) -> None:
        super().__init__("exchange non raggiungibile, riprovare")


class NoOpenPositionError(ApplicationError):
    status_code = 409

    def __init__(self, coin: str) -> None:
        super().__init__(f"nessuna posizione aperta su {coin}")
        self.coin = coin


class OrderWorkerUnavailableError(ApplicationError):
    status_code = 503

    def __init__(self) -> None:
        super().__init__("servizio di esecuzione non raggiungibile, riprovare")
