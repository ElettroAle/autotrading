from dataclasses import dataclass

from autotrading.adapters.outbound.lunarcrush.social import LUNARCRUSH_URL, TIMEOUT_SECONDS


@dataclass(frozen=True, slots=True)
class _LunarCrushSettings:
    """Where the API v4 of LunarCrush answers and how long the platform waits before the source is absent from the
    cycle: the key is the tenant's, never of the installation (R4.1.2)."""

    base_url: str = LUNARCRUSH_URL
    timeout_seconds: float = TIMEOUT_SECONDS
