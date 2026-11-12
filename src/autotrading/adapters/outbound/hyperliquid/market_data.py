from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

import requests
from hyperliquid.utils.constants import MAINNET_API_URL, TESTNET_API_URL
from hyperliquid.utils.error import ClientError, ServerError

from autotrading.adapters.outbound.hyperliquid.exchange import TIMEOUT_SECONDS, HyperliquidSdk, OfficialSdk
from autotrading.application.sources.errors import SourceUnavailableError
from autotrading.domain.sources.forecast import FORECAST
from autotrading.domain.sources.price_forecast import PricePoint

MINUTES_PER_DAY = 24 * 60
# Hyperliquid keeps only the most recent 5000 candles of each interval (info endpoint, candleSnapshot).
KEPT_CANDLES = 5000
INTERVALS = ((1, "1m"), (3, "3m"), (5, "5m"), (15, "15m"), (30, "30m"), (60, "1h"))
# A time range answers in pages: the next page starts after the last candle received.
MAX_PAGES = 20
MILLISECONDS = 1000
# An exchange that refuses, does not answer or answers in another shape: the source is absent from the cycle.
UNAVAILABLE = (ClientError, ServerError, requests.RequestException, KeyError, TypeError, InvalidOperation)


class HyperliquidPriceHistoryAdapter:
    """Closing prices of the exchange from its public candles, without credentials (R1.3.5, ADR 0043)."""

    def __init__(self, base_url: str, sdk: HyperliquidSdk | None = None, timeout: float = TIMEOUT_SECONDS) -> None:
        self._base_url = base_url
        self._sdk = sdk or OfficialSdk()
        self._timeout = timeout

    @classmethod
    def for_network(cls, *, testnet: bool, sdk: HyperliquidSdk | None = None) -> HyperliquidPriceHistoryAdapter:
        return cls(TESTNET_API_URL if testnet else MAINNET_API_URL, sdk)

    def history(self, asset: str, days: int, now: datetime) -> Sequence[PricePoint]:
        try:
            info = self._sdk.info(self._base_url, self._timeout)
            return [_point_of(candle) for candle in _all_pages(info, asset, days, now)]
        except (*UNAVAILABLE, ValueError) as error:
            raise SourceUnavailableError(FORECAST.name) from error

    def current_price(self, asset: str) -> Decimal:
        try:
            mids = self._sdk.info(self._base_url, self._timeout).all_mids()
            return Decimal(mids[asset])
        except UNAVAILABLE as error:
            raise SourceUnavailableError(FORECAST.name) from error


def interval_for(days: int) -> tuple[int, str]:
    """The finest interval whose candles over the requested days are all still kept by the exchange."""
    for minutes, name in INTERVALS:
        if days * MINUTES_PER_DAY / minutes <= KEPT_CANDLES:
            return minutes, name
    return INTERVALS[-1]


def _all_pages(info: Any, asset: str, days: int, now: datetime) -> list[Mapping[str, Any]]:
    minutes, interval = interval_for(days)
    step = minutes * 60 * MILLISECONDS
    end = _milliseconds(now)
    page_start = _milliseconds(now - timedelta(days=days))
    candles: list[Mapping[str, Any]] = []
    for _ in range(MAX_PAGES):
        page = info.candles_snapshot(asset, interval, page_start, end)
        if not page:
            return candles
        candles.extend(page)
        page_start = int(page[-1]["t"]) + step
        if page_start > end:
            return candles
    return candles


def _point_of(candle: Mapping[str, Any]) -> PricePoint:
    return PricePoint(datetime.fromtimestamp(int(candle["T"]) / MILLISECONDS, UTC), Decimal(str(candle["c"])))


def _milliseconds(moment: datetime) -> int:
    return int(moment.timestamp() * MILLISECONDS)
