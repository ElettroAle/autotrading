from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest
import requests
from hyperliquid.utils.constants import MAINNET_API_URL, TESTNET_API_URL
from hyperliquid.utils.error import ClientError, ServerError

from autotrading.adapters.outbound.hyperliquid.exchange import TIMEOUT_SECONDS
from autotrading.adapters.outbound.hyperliquid.market_data import MARKET_DATA, HyperliquidMarketDataAdapter
from autotrading.application.sources.errors import SourceUnavailableError
from autotrading.domain.sources.candle import Candle
from autotrading.domain.sources.market_snapshot import MarketSnapshot
from autotrading.domain.sources.pivot_levels import DailyRange
from autotrading.domain.sources.timeframe import Timeframe

NOW = datetime(2026, 11, 12, 10, 7, tzinfo=UTC)
NOW_MS = int(NOW.timestamp() * 1000)
MINUTE_MS = 60_000
DAY_MS = 1440 * MINUTE_MS
TODAY_MS = int(datetime(2026, 11, 12, tzinfo=UTC).timestamp() * 1000)
FIFTEEN = Timeframe(15, "15m")
BTC_CONTEXT = {"markPx": "74572.0", "midPx": "74697.0", "openInterest": "59.76604", "funding": "0.0005882896"}


def candle(open_ms: int, close: str, minutes: int = 15, **values: str) -> dict[str, Any]:
    return {"t": open_ms, "T": open_ms + minutes * MINUTE_MS - 1, "c": close, "v": "2.5", "s": "BTC", **values}


@dataclass
class FakeSdk:
    """Stands in for the info client of the official SDK: it answers the candles and contexts the test decides."""

    page: list[Any] = field(default_factory=list)
    contexts: Any = field(default_factory=lambda: [{"universe": [{"name": "ETH"}, {"name": "BTC"}]}, [{}, BTC_CONTEXT]])
    failure: Exception | None = None
    calls: list[tuple[str, Any]] = field(default_factory=list)

    def exchange(self, *_: object) -> FakeSdk:
        return self

    def info(self, base_url: str, timeout: float) -> FakeSdk:
        self.calls.append(("info", (base_url, timeout)))
        if self.failure:
            raise self.failure
        return self

    def candles_snapshot(self, name: str, interval: str, start: int, end: int) -> list[Any]:
        self.calls.append(("candles_snapshot", (name, interval, start, end)))
        return self.page

    def meta_and_asset_ctxs(self) -> Any:
        return self.contexts


def adapter(sdk: FakeSdk) -> HyperliquidMarketDataAdapter:
    return HyperliquidMarketDataAdapter(TESTNET_API_URL, sdk)


def test_the_candles_are_the_closed_ones_with_close_and_volume() -> None:
    closed = NOW_MS - 22 * MINUTE_MS
    sdk = FakeSdk(page=[candle(closed, "100.5"), candle(closed + 15 * MINUTE_MS, "101")])

    candles = adapter(sdk).candles("BTC", FIFTEEN, 2, NOW)

    assert candles == [Candle(NOW - timedelta(minutes=7), Decimal("100.5"), Decimal("2.5"))]
    assert sdk.calls == [
        ("info", (TESTNET_API_URL, TIMEOUT_SECONDS)),
        ("candles_snapshot", ("BTC", "15m", NOW_MS - 3 * 15 * MINUTE_MS, NOW_MS)),
    ]


def test_only_the_last_candles_asked_are_kept() -> None:
    first = NOW_MS - 67 * MINUTE_MS
    sdk = FakeSdk(page=[candle(first + index * 15 * MINUTE_MS, str(index)) for index in range(4)])

    candles = adapter(sdk).candles("BTC", FIFTEEN, 2, NOW)

    assert [candle.close for candle in candles] == [Decimal(2), Decimal(3)]


def test_a_candle_closing_exactly_now_is_closed_and_one_closing_later_is_not() -> None:
    closing_now = candle(NOW_MS - 15 * MINUTE_MS, "7")
    closing_later = candle(NOW_MS - 15 * MINUTE_MS + 1, "8")

    candles = adapter(FakeSdk(page=[closing_now, closing_later])).candles("BTC", FIFTEEN, 2, NOW)

    assert [(candle.closed_at, candle.close) for candle in candles] == [(NOW, Decimal(7))]


def test_the_snapshot_reads_the_context_of_the_asset() -> None:
    assert adapter(FakeSdk()).snapshot("BTC") == MarketSnapshot(
        Decimal("74572.0"), Decimal("74697.0"), Decimal("59.76604"), Decimal("0.0005882896")
    )


def test_the_previous_day_is_the_daily_candle_of_yesterday_utc() -> None:
    yesterday = TODAY_MS - DAY_MS
    sdk = FakeSdk(
        page=[
            candle(yesterday - DAY_MS, "1", 1440, h="2", l="0"),
            candle(yesterday, "100", 1440, h="110", l="90"),
            candle(TODAY_MS, "5", 1440, h="6", l="4"),
        ]
    )

    day = adapter(sdk).previous_day("BTC", NOW)

    assert day == DailyRange(high=Decimal(110), low=Decimal(90), close=Decimal(100))
    assert sdk.calls[-1] == ("candles_snapshot", ("BTC", "1d", yesterday, TODAY_MS - 1))


def test_a_previous_day_missing_makes_the_source_unavailable() -> None:
    with pytest.raises(SourceUnavailableError) as raised:
        adapter(FakeSdk(page=[candle(TODAY_MS, "5", 1440, h="6", l="4")])).previous_day("BTC", NOW)

    assert raised.value.source == MARKET_DATA


@pytest.mark.parametrize(
    "failure",
    [ClientError(429, None, "rate limited", None), ServerError(500, "down"), requests.ConnectionError("unreachable")],
)
def test_an_exchange_that_does_not_answer_makes_the_source_unavailable(failure: Exception) -> None:
    market = adapter(FakeSdk(failure=failure))

    for read in (
        lambda: market.candles("BTC", FIFTEEN, 1, NOW),
        lambda: market.snapshot("BTC"),
        lambda: market.previous_day("BTC", NOW),
    ):
        with pytest.raises(SourceUnavailableError) as raised:
            read()
        assert raised.value.source == MARKET_DATA


@pytest.mark.parametrize(
    "page",
    [
        [{"t": NOW_MS, "c": "1"}],
        [candle(NOW_MS - 20 * MINUTE_MS, "not a price")],
        [{**candle(NOW_MS - 20 * MINUTE_MS, "1"), "v": None}],
        ["x"],
    ],
)
def test_candles_in_another_shape_make_the_source_unavailable(page: list[Any]) -> None:
    with pytest.raises(SourceUnavailableError):
        adapter(FakeSdk(page=page)).candles("BTC", FIFTEEN, 1, NOW)


@pytest.mark.parametrize("day", [{"t": "x"}, {"t": TODAY_MS - DAY_MS, "h": "1", "l": "x", "c": "1"}])
def test_a_previous_day_in_another_shape_makes_the_source_unavailable(day: dict[str, Any]) -> None:
    with pytest.raises(SourceUnavailableError):
        adapter(FakeSdk(page=[day])).previous_day("BTC", NOW)


@pytest.mark.parametrize(
    "contexts",
    [
        [{"universe": [{"name": "ETH"}]}, [{}]],
        [{"universe": [{"name": "BTC"}]}, []],
        [{"universe": [{"name": "BTC"}]}, [{**BTC_CONTEXT, "midPx": None}]],
        [{"universe": [{"name": "BTC"}]}, [{**BTC_CONTEXT, "funding": "x"}]],
        None,
    ],
)
def test_a_missing_or_malformed_context_makes_the_source_unavailable(contexts: Any) -> None:
    with pytest.raises(SourceUnavailableError):
        adapter(FakeSdk(contexts=contexts)).snapshot("BTC")


@pytest.mark.parametrize(("testnet", "url"), [(True, TESTNET_API_URL), (False, MAINNET_API_URL)])
def test_the_network_chooses_the_address_of_the_exchange(testnet: bool, url: str) -> None:
    sdk = FakeSdk()

    HyperliquidMarketDataAdapter.for_network(testnet=testnet, sdk=sdk).snapshot("BTC")

    assert sdk.calls[0] == ("info", (url, TIMEOUT_SECONDS))
