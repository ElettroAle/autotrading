import httpx

from autotrading.adapters.outbound.binance.configuration import _BinanceSettings
from autotrading.adapters.outbound.binance.volumes import BinanceVolumesAdapter


def binance_adapters() -> BinanceVolumesAdapter:
    """The volumes and the order book of Binance, from its public market data without a key (ADR
    fonte-volumi-con-adapter-binance)."""
    settings = _BinanceSettings()
    return BinanceVolumesAdapter(httpx.Client(base_url=settings.base_url, timeout=settings.timeout_seconds))
