from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

import requests
from hyperliquid.utils.constants import MAINNET_API_URL, TESTNET_API_URL
from hyperliquid.utils.error import ClientError, ServerError

from autotrading.adapters.outbound.hyperliquid.exchange import TIMEOUT_SECONDS, HyperliquidSdkAdapter
from autotrading.application.sources.errors import SourceUnavailableError, TimeframeNotSupportedError
from autotrading.domain.sources.candle import Candle
from autotrading.domain.sources.forecast import FORECAST
from autotrading.domain.sources.market_snapshot import MarketSnapshot
from autotrading.domain.sources.pivot_levels import DailyRange
from autotrading.domain.sources.price_forecast import PricePoint
from autotrading.domain.sources.timeframe import Timeframe

MINUTES_PER_HOUR = 60
MINUTES_PER_DAY = 24 * MINUTES_PER_HOUR
# Hyperliquid keeps only the most recent 5000 candles of each interval (info endpoint, candleSnapshot).
KEPT_CANDLES = 5000
# The candle intervals of candleSnapshot by their span in minutes; the monthly one (1M) has no fixed span.
CANDLE_INTERVALS = {
    1: "1m",
    3: "3m",
    5: "5m",
    15: "15m",
    30: "30m",
    60: "1h",
    120: "2h",
    240: "4h",
    480: "8h",
    720: "12h",
    MINUTES_PER_DAY: "1d",
    3 * MINUTES_PER_DAY: "3d",
    7 * MINUTES_PER_DAY: "1w",
}
# A time range answers in pages: the next page starts after the last candle received.
MAX_PAGES = 20
MILLISECONDS = 1000
DAY = CANDLE_INTERVALS[MINUTES_PER_DAY]
# Never coarser than one hour: the 15-minute forecast would become a fraction of a step (ADR 0043).
INTERVALS = tuple((minutes, name) for minutes, name in CANDLE_INTERVALS.items() if minutes <= MINUTES_PER_HOUR)
MARKET_DATA = "dati di mercato di Hyperliquid"
# An exchange that refuses, does not answer or answers in another shape: the source is absent from the cycle.
UNAVAILABLE = (ClientError, ServerError, requests.RequestException, KeyError, TypeError, InvalidOperation)


class HyperliquidPriceHistoryAdapter:
    """Closing prices of the exchange from its public candles, without credentials (R1.3.5, ADR 0043)."""

    def __init__(
        self, base_url: str, sdk: HyperliquidSdkAdapter | None = None, timeout: float = TIMEOUT_SECONDS
    ) -> None:
        self._base_url = base_url
        self._sdk = sdk or HyperliquidSdkAdapter()
        self._timeout = timeout

    @classmethod
    def for_network(cls, *, testnet: bool, sdk: HyperliquidSdkAdapter | None = None) -> HyperliquidPriceHistoryAdapter:
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


class HyperliquidMarketDataAdapter:
    """Candles, current values and previous day of an asset from the public info endpoint (R1.3.3, R1.3.4, ADR 0057).

    The candle still open is left out: its close and its volume change until it closes.
    """

    def __init__(
        self, base_url: str, sdk: HyperliquidSdkAdapter | None = None, timeout: float = TIMEOUT_SECONDS
    ) -> None:
        self._base_url = base_url
        self._sdk = sdk or HyperliquidSdkAdapter()
        self._timeout = timeout

    @classmethod
    def for_network(cls, *, testnet: bool, sdk: HyperliquidSdkAdapter | None = None) -> HyperliquidMarketDataAdapter:
        return cls(TESTNET_API_URL if testnet else MAINNET_API_URL, sdk)

    def timeframes(self) -> Sequence[Timeframe]:
        return tuple(Timeframe(minutes) for minutes in CANDLE_INTERVALS)

    def candles(self, asset: str, timeframe: Timeframe, count: int, now: datetime) -> Sequence[Candle]:
        interval = CANDLE_INTERVALS.get(timeframe.minutes)
        if interval is None:
            raise TimeframeNotSupportedError(timeframe.minutes)
        end = _milliseconds(now)
        start = _milliseconds(now - timedelta(minutes=timeframe.minutes * (count + 1)))
        try:
            page = self._info().candles_snapshot(asset, interval, start, end)
            closed = [_candle_of(candle) for candle in page if int(candle["T"]) < end]
        except (*UNAVAILABLE, ValueError) as error:
            raise SourceUnavailableError(MARKET_DATA) from error
        return closed[-count:]

    def snapshot(self, asset: str) -> MarketSnapshot:
        try:
            meta, contexts = self._info().meta_and_asset_ctxs()
            names = [market["name"] for market in meta["universe"]]
            context = contexts[names.index(asset)]
            return MarketSnapshot(
                price=Decimal(context["markPx"]),
                mid=Decimal(context["midPx"]),
                open_interest=Decimal(context["openInterest"]),
                funding_rate=Decimal(context["funding"]),
            )
        except (*UNAVAILABLE, ValueError, IndexError) as error:
            raise SourceUnavailableError(MARKET_DATA) from error

    def previous_day(self, asset: str, now: datetime) -> DailyRange:
        today = datetime(now.year, now.month, now.day, tzinfo=UTC)
        yesterday = _milliseconds(today - timedelta(days=1))
        try:
            page = self._info().candles_snapshot(asset, DAY, yesterday, _milliseconds(today) - 1)
            days = [_range_of(candle) for candle in page if int(candle["t"]) == yesterday]
        except (*UNAVAILABLE, ValueError) as error:
            raise SourceUnavailableError(MARKET_DATA) from error
        if not days:
            raise SourceUnavailableError(MARKET_DATA)
        return days[0]

    def _info(self) -> Any:
        return self._sdk.info(self._base_url, self._timeout)


def _candle_of(candle: Mapping[str, Any]) -> Candle:
    closed_at = datetime.fromtimestamp((int(candle["T"]) + 1) / MILLISECONDS, UTC)
    return Candle(closed_at, Decimal(str(candle["c"])), Decimal(str(candle["v"])))


def _range_of(candle: Mapping[str, Any]) -> DailyRange:
    return DailyRange(high=Decimal(str(candle["h"])), low=Decimal(str(candle["l"])), close=Decimal(str(candle["c"])))
