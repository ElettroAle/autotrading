from collections.abc import Mapping

import requests
from hyperliquid.utils.constants import MAINNET_API_URL, TESTNET_API_URL
from hyperliquid.utils.error import ClientError, ServerError

from autotrading.adapters.outbound.hyperliquid.exchange import (
    MIN_ORDER_VALUE,
    TIMEOUT_SECONDS,
    HyperliquidSdkAdapter,
)
from autotrading.application.flows.errors import FlowExchangeUnavailableError
from autotrading.domain.flows.risk_check import AssetLimits

SHAPE_ERRORS = (KeyError, TypeError, AttributeError)


class HyperliquidMarketsAdapter:
    """The assets Hyperliquid trades now and their limits, from its public metadata: no credentials (R1.1.1, R1.5.2)."""

    def __init__(
        self, base_url: str, sdk: HyperliquidSdkAdapter | None = None, timeout: float = TIMEOUT_SECONDS
    ) -> None:
        self._base_url = base_url
        self._sdk = sdk or HyperliquidSdkAdapter()
        self._timeout = timeout

    @classmethod
    def for_network(cls, *, testnet: bool, sdk: HyperliquidSdkAdapter | None = None) -> HyperliquidMarketsAdapter:
        return cls(TESTNET_API_URL if testnet else MAINNET_API_URL, sdk)

    @property
    def base_url(self) -> str:
        return self._base_url

    def tradable_assets(self) -> frozenset[str]:
        return frozenset(self._listed())

    def limits(self, asset: str) -> AssetLimits | None:
        """The maximum leverage of the asset from the metadata, and the minimum order value of the exchange."""
        entry = self._listed().get(asset)
        if entry is None:
            return None
        try:
            return AssetLimits(int(str(entry["maxLeverage"])), MIN_ORDER_VALUE)
        except (*SHAPE_ERRORS, ValueError) as error:
            raise FlowExchangeUnavailableError from error

    def _listed(self) -> dict[str, Mapping[str, object]]:
        """The assets not delisted, by name."""
        try:
            universe = self._sdk.info(self._base_url, self._timeout).meta()["universe"]
            return {_name(asset): asset for asset in universe if not asset.get("isDelisted", False)}
        except (ClientError, ServerError, requests.RequestException, *SHAPE_ERRORS) as error:
            raise FlowExchangeUnavailableError from error


def _name(asset: Mapping[str, object]) -> str:
    return str(asset["name"])
