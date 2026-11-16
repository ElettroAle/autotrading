from collections.abc import Mapping
from decimal import Decimal, InvalidOperation

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
UNAVAILABLE = (ClientError, ServerError, requests.RequestException, *SHAPE_ERRORS, ValueError, InvalidOperation)


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
        """The maximum leverage of the asset from the metadata, the minimum order value of the exchange and the mid
        price of the asset, from one reading of the market (R1.5.2, R3.1.1).
        """
        try:
            info = self._sdk.info(self._base_url, self._timeout)
            entry = _listed_in(info.meta()).get(asset)
            if entry is None:
                return None
            return AssetLimits(int(str(entry["maxLeverage"])), MIN_ORDER_VALUE, _market_price(info.all_mids(), asset))
        except UNAVAILABLE as error:
            raise FlowExchangeUnavailableError from error

    def _listed(self) -> dict[str, Mapping[str, object]]:
        try:
            return _listed_in(self._sdk.info(self._base_url, self._timeout).meta())
        except (ClientError, ServerError, requests.RequestException, *SHAPE_ERRORS) as error:
            raise FlowExchangeUnavailableError from error


def _listed_in(meta: Mapping[str, list[Mapping[str, object]]]) -> dict[str, Mapping[str, object]]:
    """The assets not delisted, by name."""
    return {_name(asset): asset for asset in meta["universe"] if not asset.get("isDelisted", False)}


def _market_price(mids: Mapping[str, object], asset: str) -> Decimal:
    price = Decimal(str(mids[asset]))
    if not price > 0:
        raise FlowExchangeUnavailableError
    return price


def _name(asset: Mapping[str, object]) -> str:
    return str(asset["name"])
