from dataclasses import dataclass

from autotrading.adapters.outbound.binance.volumes import BINANCE_URL, TIMEOUT_SECONDS


@dataclass(frozen=True, slots=True)
class _BinanceSettings:
    """Where the public market data of Binance answer and how long the platform waits before the source is absent from
    the cycle: no key, the data are public (ADR fonte-volumi-con-adapter-binance)."""

    base_url: str = BINANCE_URL
    timeout_seconds: float = TIMEOUT_SECONDS
