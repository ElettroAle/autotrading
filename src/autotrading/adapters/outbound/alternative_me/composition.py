import httpx

from autotrading.adapters.outbound.alternative_me.configuration import _AlternativeMeSettings
from autotrading.adapters.outbound.alternative_me.sentiment import AlternativeMeSentimentAdapter


def alternative_me_adapters() -> AlternativeMeSentimentAdapter:
    """The Fear & Greed Index of alternative.me, from its public endpoint without a key (ADR 0033)."""
    settings = _AlternativeMeSettings()
    return AlternativeMeSentimentAdapter(httpx.Client(timeout=settings.timeout_seconds))
