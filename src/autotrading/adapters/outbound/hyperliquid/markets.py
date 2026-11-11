from typing import Any

import requests
from hyperliquid.utils.constants import MAINNET_API_URL, TESTNET_API_URL
from hyperliquid.utils.error import ClientError, ServerError

from autotrading.adapters.outbound.hyperliquid.exchange import TIMEOUT_SECONDS, HyperliquidSdk, OfficialSdk
from autotrading.application.flows.errors import FlowExchangeUnavailableError

SHAPE_ERRORS = (KeyError, TypeError, AttributeError)


class HyperliquidMarketsAdapter:
    """The assets Hyperliquid trades now, read from its public metadata: no credentials needed (R1.1.1)."""

    def __init__(self, base_url: str, sdk: HyperliquidSdk | None = None, timeout: float = TIMEOUT_SECONDS) -> None:
        self._base_url = base_url
        self._sdk = sdk or OfficialSdk()
        self._timeout = timeout

    @classmethod
    def for_network(cls, *, testnet: bool, sdk: HyperliquidSdk | None = None) -> HyperliquidMarketsAdapter:
        return cls(TESTNET_API_URL if testnet else MAINNET_API_URL, sdk)

    @property
    def base_url(self) -> str:
        return self._base_url

    def tradable_assets(self) -> frozenset[str]:
        try:
            universe = self._sdk.info(self._base_url, self._timeout).meta()["universe"]
            return frozenset(_name(asset) for asset in universe if not asset.get("isDelisted", False))
        except (ClientError, ServerError, requests.RequestException, *SHAPE_ERRORS) as error:
            raise FlowExchangeUnavailableError from error


def _name(asset: Any) -> str:
    name: str = asset["name"]
    return name
