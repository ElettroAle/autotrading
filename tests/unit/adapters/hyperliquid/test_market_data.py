from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, override

import pytest
import requests
from eth_account.signers.local import LocalAccount
from hyperliquid.utils.constants import MAINNET_API_URL, TESTNET_API_URL
from hyperliquid.utils.error import ClientError, ServerError

from autotrading.adapters.outbound.hyperliquid.exchange import TIMEOUT_SECONDS, HyperliquidSdkAdapter
from autotrading.adapters.outbound.hyperliquid.market_data import (
    MAX_PAGES,
    HyperliquidPriceHistoryAdapter,
    interval_for,
)
from autotrading.application.sources.errors import SourceUnavailableError
from autotrading.domain.sources.price_forecast import PricePoint

NOW = datetime(2026, 11, 12, 10, 0, tzinfo=UTC)
NOW_MS = int(NOW.timestamp() * 1000)
MINUTE_MS = 60_000


def candle(open_ms: int, close: str, minutes: int = 1) -> dict[str, Any]:
    return {"t": open_ms, "T": open_ms + minutes * MINUTE_MS - 1, "c": close, "s": "BTC", "i": f"{minutes}m"}


@dataclass
class FakeSdk(HyperliquidSdkAdapter):
    """Stands in for the info client of the official SDK: it answers the pages and prices the test decides."""

    pages: list[list[dict[str, Any]]] = field(default_factory=list)
    mids: Any = field(default_factory=lambda: {"BTC": "74684.0"})
    failure: Exception | None = None
    calls: list[tuple[str, Any]] = field(default_factory=list)

    @override
    def exchange(self, wallet: LocalAccount, base_url: str, account_address: str, timeout: float) -> FakeSdk:
        return self

    def info(self, base_url: str, timeout: float) -> FakeSdk:
        self.calls.append(("info", (base_url, timeout)))
        if self.failure:
            raise self.failure
        return self

    def candles_snapshot(self, name: str, interval: str, start: int, end: int) -> list[dict[str, Any]]:
        self.calls.append(("candles_snapshot", (name, interval, start, end)))
        return self.pages.pop(0) if self.pages else []

    def all_mids(self) -> Any:
        return self.mids


@pytest.mark.parametrize(
    ("days", "expected"),
    [(1, (1, "1m")), (3, (1, "1m")), (4, (3, "3m")), (10, (3, "3m")), (17, (5, "5m")), (90, (30, "30m"))],
)
def test_the_interval_is_the_finest_whose_candles_the_exchange_still_keeps(
    days: int, expected: tuple[int, str]
) -> None:
    assert interval_for(days) == expected


def test_a_depth_beyond_every_interval_takes_the_coarsest() -> None:
    assert interval_for(500) == (60, "1h")


def test_the_history_is_read_from_the_closing_prices_of_the_candles() -> None:
    start = NOW_MS - 2 * MINUTE_MS
    sdk = FakeSdk(pages=[[candle(start, "100.5"), candle(start + MINUTE_MS, "101")]])

    points = HyperliquidPriceHistoryAdapter(TESTNET_API_URL, sdk).history("BTC", 1, NOW)

    assert points == [
        PricePoint(NOW - timedelta(minutes=1, milliseconds=1), Decimal("100.5")),
        PricePoint(NOW - timedelta(milliseconds=1), Decimal(101)),
    ]
    assert sdk.calls[:2] == [
        ("info", (TESTNET_API_URL, TIMEOUT_SECONDS)),
        ("candles_snapshot", ("BTC", "1m", NOW_MS - 1440 * MINUTE_MS, NOW_MS)),
    ]


def test_the_next_page_starts_one_interval_after_the_last_candle_received() -> None:
    first = NOW_MS - 1440 * MINUTE_MS
    sdk = FakeSdk(pages=[[candle(first, "1")], [candle(first + MINUTE_MS, "2")]])

    points = HyperliquidPriceHistoryAdapter(TESTNET_API_URL, sdk).history("BTC", 1, NOW)

    assert [point.price for point in points] == [Decimal(1), Decimal(2)]
    pages = [arguments for name, arguments in sdk.calls if name == "candles_snapshot"]
    assert pages == [
        ("BTC", "1m", first, NOW_MS),
        ("BTC", "1m", first + MINUTE_MS, NOW_MS),
        ("BTC", "1m", first + 2 * MINUTE_MS, NOW_MS),
    ]


def test_the_reading_stops_once_the_last_candle_reaches_now() -> None:
    sdk = FakeSdk(pages=[[candle(NOW_MS, "1")], [candle(NOW_MS, "2")]])

    points = HyperliquidPriceHistoryAdapter(TESTNET_API_URL, sdk).history("BTC", 1, NOW)

    assert [point.price for point in points] == [Decimal(1)]


def test_the_reading_stops_after_the_maximum_number_of_pages() -> None:
    first = NOW_MS - 1440 * MINUTE_MS
    sdk = FakeSdk(pages=[[candle(first + index * MINUTE_MS, str(index))] for index in range(MAX_PAGES + 5)])

    points = HyperliquidPriceHistoryAdapter(TESTNET_API_URL, sdk).history("BTC", 1, NOW)

    assert len(points) == MAX_PAGES


def test_the_current_price_is_the_mid_price_of_the_exchange() -> None:
    assert HyperliquidPriceHistoryAdapter(TESTNET_API_URL, FakeSdk()).current_price("BTC") == Decimal("74684.0")


@pytest.mark.parametrize(
    "failure",
    [
        ClientError(429, None, "rate limited", None),
        ServerError(500, "down"),
        requests.ConnectionError("unreachable"),
    ],
)
def test_an_exchange_that_does_not_answer_makes_the_source_unavailable(failure: Exception) -> None:
    adapter = HyperliquidPriceHistoryAdapter(TESTNET_API_URL, FakeSdk(failure=failure))

    with pytest.raises(SourceUnavailableError) as history_raised:
        adapter.history("BTC", 7, NOW)
    with pytest.raises(SourceUnavailableError) as price_raised:
        adapter.current_price("BTC")

    assert history_raised.value.source == price_raised.value.source == "forecast"


@pytest.mark.parametrize(
    "page",
    [
        [{"t": NOW_MS, "c": "1"}],
        [{"t": NOW_MS, "T": NOW_MS, "c": "not a price"}],
        [{"t": "x", "T": NOW_MS, "c": "1"}],
        ["x"],
    ],
)
def test_candles_in_another_shape_make_the_source_unavailable(page: list[Any]) -> None:
    with pytest.raises(SourceUnavailableError):
        HyperliquidPriceHistoryAdapter(TESTNET_API_URL, FakeSdk(pages=[page])).history("BTC", 1, NOW)


@pytest.mark.parametrize("mids", [{}, {"BTC": "not a price"}, None])
def test_a_missing_or_malformed_mid_price_makes_the_source_unavailable(mids: Any) -> None:
    with pytest.raises(SourceUnavailableError):
        HyperliquidPriceHistoryAdapter(TESTNET_API_URL, FakeSdk(mids=mids)).current_price("BTC")


@pytest.mark.parametrize(("testnet", "url"), [(True, TESTNET_API_URL), (False, MAINNET_API_URL)])
def test_the_network_chooses_the_address_of_the_exchange(testnet: bool, url: str) -> None:
    sdk = FakeSdk()

    HyperliquidPriceHistoryAdapter.for_network(testnet=testnet, sdk=sdk).current_price("BTC")

    assert sdk.calls[0] == ("info", (url, TIMEOUT_SECONDS))
