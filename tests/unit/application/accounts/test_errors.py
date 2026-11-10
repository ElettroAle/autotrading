from autotrading.application.accounts.errors import UnsupportedExchangeError
from autotrading.domain.accounts.exchange_name import ExchangeName


def test_unsupported_exchange_lists_the_supported_ones_in_order() -> None:
    error = UnsupportedExchangeError(ExchangeName("Binance"), {"Hyperliquid": 1, "Bybit": 2})

    assert (str(error), error.supported) == ("exchange non supportato", ("Bybit", "Hyperliquid"))
