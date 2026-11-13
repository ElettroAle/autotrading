"""The adapters of CoinMarketCap, built with their own client (ADR 0033, ADR 0034)."""

from autotrading.adapters.outbound.coinmarketcap.composition import coinmarketcap_adapters
from autotrading.adapters.outbound.coinmarketcap.configuration import _CoinMarketCapSettings
from autotrading.adapters.outbound.coinmarketcap.sentiment import TIMEOUT_SECONDS, CoinMarketCapSentimentAdapter


def test_the_composition_builds_the_adapter_of_the_endpoint() -> None:
    assert isinstance(coinmarketcap_adapters(), CoinMarketCapSentimentAdapter)


def test_the_settings_wait_the_declared_timeout() -> None:
    assert _CoinMarketCapSettings().timeout_seconds == TIMEOUT_SECONDS
