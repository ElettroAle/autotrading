import httpx

from autotrading.adapters.outbound.coinmarketcap.configuration import _CoinMarketCapSettings
from autotrading.adapters.outbound.coinmarketcap.sentiment import CoinMarketCapSentimentAdapter


def coinmarketcap_adapters() -> CoinMarketCapSentimentAdapter:
    """The Fear and Greed Index of CoinMarketCap, from its public prefix without a key (ADR 0033)."""
    settings = _CoinMarketCapSettings()
    return CoinMarketCapSentimentAdapter(httpx.Client(timeout=settings.timeout_seconds))
