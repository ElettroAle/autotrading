from dataclasses import dataclass

from autotrading.adapters.outbound.arkham.whale_transfers import ARKHAM_URL, TIMEOUT_SECONDS


@dataclass(frozen=True, slots=True)
class _ArkhamSettings:
    """Where the Intel API of Arkham answers and how long the platform waits before the source is absent from the cycle:
    the key is the tenant's, never of the installation (R4.1.2)."""

    base_url: str = ARKHAM_URL
    timeout_seconds: float = TIMEOUT_SECONDS
