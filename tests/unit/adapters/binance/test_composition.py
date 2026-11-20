"""The adapter of Binance, built with its own client on the address of the market data (ADR
fonte-volumi-con-adapter-binance)."""

from autotrading.adapters.outbound.binance.composition import binance_adapters
from autotrading.adapters.outbound.binance.configuration import _BinanceSettings
from autotrading.adapters.outbound.binance.volumes import BINANCE_URL, TIMEOUT_SECONDS, BinanceVolumesAdapter


def test_the_composition_builds_the_adapter_of_the_market_data() -> None:
    assert isinstance(binance_adapters(), BinanceVolumesAdapter)


def test_the_settings_reach_the_market_data_and_wait_the_declared_timeout() -> None:
    settings = _BinanceSettings()

    assert (settings.base_url, settings.timeout_seconds) == (BINANCE_URL, TIMEOUT_SECONDS)
    assert BINANCE_URL == "https://data-api.binance.vision"
