import httpx

from autotrading.adapters.outbound.arkham.configuration import _ArkhamSettings
from autotrading.adapters.outbound.arkham.whale_transfers import ArkhamWhaleTransfersAdapter


def arkham_adapters() -> ArkhamWhaleTransfersAdapter:
    """The large transfers of Arkham, read with the key each tenant gives the adapter (ADR
    fonte-whale-con-adapter-arkham)."""
    settings = _ArkhamSettings()
    return ArkhamWhaleTransfersAdapter(httpx.Client(base_url=settings.base_url, timeout=settings.timeout_seconds))
