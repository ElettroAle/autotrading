"""Fake of the limits an exchange sets on each asset."""

from dataclasses import replace
from decimal import Decimal

from autotrading.domain.flows.risk_check import AssetLimits

DEFAULT_LIMITS = AssetLimits(max_leverage=50, min_order_value=Decimal(10))


class FakeExchangeLimitsAdapter:
    """An exchange that trades the assets it was told to, each with the default limits unless set otherwise."""

    def __init__(self, assets: frozenset[str] = frozenset({"BTC", "ETH", "SOL"})) -> None:
        self._limits = dict.fromkeys(assets, DEFAULT_LIMITS)

    def set(self, asset: str, *, max_leverage: int | None = None, min_order_value: Decimal | None = None) -> None:
        current = self._limits.get(asset, DEFAULT_LIMITS)
        self._limits[asset] = replace(
            current,
            max_leverage=current.max_leverage if max_leverage is None else max_leverage,
            min_order_value=current.min_order_value if min_order_value is None else min_order_value,
        )

    def limits(self, asset: str) -> AssetLimits | None:
        return self._limits.get(asset)
