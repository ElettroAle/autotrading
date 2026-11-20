import httpx

from autotrading.adapters.outbound.lunarcrush.configuration import _LunarCrushSettings
from autotrading.adapters.outbound.lunarcrush.social import LunarCrushSocialAdapter


def lunarcrush_adapters() -> LunarCrushSocialAdapter:
    """The social data of LunarCrush, read with the key each tenant gives the adapter (ADR
    fonte-social-con-adapter-lunarcrush)."""
    settings = _LunarCrushSettings()
    return LunarCrushSocialAdapter(httpx.Client(base_url=settings.base_url, timeout=settings.timeout_seconds))
