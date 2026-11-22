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
from autotrading.adapters.outbound.hyperliquid.market_data import MARKET_DATA, HyperliquidMarketDataAdapter
from autotrading.application.sources.errors import SourceUnavailableError, TimeframeNotSupportedError
from autotrading.domain.sources.candle import Candle
from autotrading.domain.sources.market_snapshot import MarketSnapshot
from autotrading.domain.sources.source_adapter_declaration import SourceAdapterDeclaration
from autotrading.domain.sources.timeframe import Timeframe

NOW = datetime(2026, 11, 12, 10, 7, tzinfo=UTC)
NOW_MS = int(NOW.timestamp() * 1000)
MINUTE_MS = 60_000
DAY_MS = 1440 * MINUTE_MS
TODAY_MS = int(datetime(2026, 11, 12, tzinfo=UTC).timestamp() * 1000)
FIFTEEN = Timeframe(15)
BTC_CONTEXT = {"markPx": "74572.0", "midPx": "74697.0", "openInterest": "59.76604", "funding": "0.0005882896"}


def candle(open_ms: int, close: str, minutes: int = 15, **values: str) -> dict[str, Any]:
    candle = {"t": open_ms, "T": open_ms + minutes * MINUTE_MS - 1, "c": close, "v": "2.5", "h": "110", "l": "90"}
    return {**candle, "s": "BTC", **values}


@dataclass
class FakeSdk(HyperliquidSdkAdapter):
    """Stands in for the info client of the official SDK: it answers the candles and contexts the test decides."""

    page: list[Any] = field(default_factory=list)
    contexts: Any = field(default_factory=lambda: [{"universe": [{"name": "ETH"}, {"name": "BTC"}]}, [{}, BTC_CONTEXT]])
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

    def candles_snapshot(self, name: str, interval: str, start: int, end: int) -> list[Any]:
        self.calls.append(("candles_snapshot", (name, interval, start, end)))
        return self.page

    def meta_and_asset_ctxs(self) -> Any:
        return self.contexts


def adapter(sdk: FakeSdk) -> HyperliquidMarketDataAdapter:
    return HyperliquidMarketDataAdapter(TESTNET_API_URL, sdk)


def test_the_market_data_declare_the_adapter_of_indicators_and_pivots_without_configuration_and_with_history() -> None:
    assert adapter(FakeSdk()).declaration() == SourceAdapterDeclaration(
        "Hyperliquid",
        "Dati di mercato pubblici di Hyperliquid: candele chiuse, mark price, open interest e funding rate.",
        (),
        (),
        offers_history=True,
    )


def test_the_candles_are_the_closed_ones_with_close_volume_high_and_low() -> None:
    closed = NOW_MS - 22 * MINUTE_MS
    sdk = FakeSdk(page=[candle(closed, "100.5"), candle(closed + 15 * MINUTE_MS, "101")])

    candles = adapter(sdk).candles("BTC", FIFTEEN, 2, NOW)

    assert candles == [Candle(NOW - timedelta(minutes=7), Decimal("100.5"), Decimal("2.5"), Decimal(110), Decimal(90))]
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


def test_the_published_intervals_are_those_of_hyperliquid_from_the_finest() -> None:
    assert [timeframe.minutes for timeframe in adapter(FakeSdk()).timeframes()] == [
        1,
        3,
        5,
        15,
        30,
        60,
        120,
        240,
        480,
        720,
        1440,
        4320,
        10080,
    ]


@pytest.mark.parametrize(
    ("minutes", "interval"),
    [(1, "1m"), (60, "1h"), (120, "2h"), (240, "4h"), (720, "12h"), (1440, "1d"), (10080, "1w")],
)
def test_the_candles_are_asked_with_the_interval_name_of_hyperliquid(minutes: int, interval: str) -> None:
    sdk = FakeSdk()

    adapter(sdk).candles("BTC", Timeframe(minutes), 1, NOW)

    assert sdk.calls[-1][1][1] == interval


def test_an_interval_hyperliquid_does_not_publish_is_refused_before_asking() -> None:
    sdk = FakeSdk()

    with pytest.raises(TimeframeNotSupportedError) as raised:
        adapter(sdk).candles("BTC", Timeframe(10), 1, NOW)

    assert raised.value.minutes == 10
    assert sdk.calls == []


def test_the_snapshot_reads_the_context_of_the_asset() -> None:
    assert adapter(FakeSdk()).snapshot("BTC") == MarketSnapshot(
        Decimal("74572.0"), Decimal("74697.0"), Decimal("59.76604"), Decimal("0.0005882896")
    )


@pytest.mark.parametrize(
    "failure",
    [ClientError(429, None, "rate limited", None), ServerError(500, "down"), requests.ConnectionError("unreachable")],
)
def test_an_exchange_that_does_not_answer_makes_the_source_unavailable(failure: Exception) -> None:
    market = adapter(FakeSdk(failure=failure))

    for read in (
        lambda: market.candles("BTC", FIFTEEN, 1, NOW),
        lambda: market.snapshot("BTC"),
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
