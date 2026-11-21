"""The market data adapter against the answers of the public info endpoint of the Hyperliquid testnet, recorded live on
21 November 2026 at 20:09 UTC through the official SDK, without credentials (ADR fonti-provate-su-risposte-registrate).

- Every answer: POST https://api.hyperliquid-testnet.xyz/info, the body of the request in its recording
- meta: the perpetual markets the SDK reads before every client
- 429: the rate limit, https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/rate-limits-and-user-limits
"""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from hyperliquid.utils.constants import TESTNET_API_URL

from autotrading.adapters.outbound.hyperliquid.market_data import MARKET_DATA, HyperliquidMarketDataAdapter
from autotrading.application.sources.errors import SourceUnavailableError
from autotrading.domain.sources.candle import Candle
from autotrading.domain.sources.market_snapshot import MarketSnapshot
from autotrading.domain.sources.pivot_levels import DailyRange
from autotrading.domain.sources.timeframe import LONG_TIMEFRAME, Timeframe
from tests.support.recorded_answers import RecordedInfoSdk, RecordedService

pytestmark = pytest.mark.integration

NOW = datetime(2026, 11, 21, 20, 9, tzinfo=UTC)
METADATA = ("meta",)
INFO_URL = f"{TESTNET_API_URL}/info"
LAST_CLOSED = datetime(2026, 11, 21, 20, 0, tzinfo=UTC)
LAST_CANDLES = {
    15: Candle(LAST_CLOSED, Decimal("61012.0"), Decimal("0.22041"), Decimal("61252.0"), Decimal("60813.0")),
    LONG_TIMEFRAME.minutes: Candle(
        LAST_CLOSED, Decimal("61012.0"), Decimal("4.13193"), Decimal("61420.0"), Decimal("59523.0")
    ),
}
CANDLE_REQUESTS = {
    15: {"coin": "BTC", "interval": "15m", "startTime": 1795191840000, "endTime": 1795291740000},
    LONG_TIMEFRAME.minutes: {"coin": "BTC", "interval": "4h", "startTime": 1793693340000, "endTime": 1795291740000},
}


def market(service: RecordedService) -> HyperliquidMarketDataAdapter:
    return HyperliquidMarketDataAdapter(TESTNET_API_URL, RecordedInfoSdk(service))


@pytest.mark.parametrize(
    ("timeframe", "answer"), [(Timeframe(15), "candles_btc_15m"), (LONG_TIMEFRAME, "candles_btc_4h")]
)
def test_the_recorded_candles_are_the_closed_ones_asked(timeframe: Timeframe, answer: str) -> None:
    candles = market(RecordedService("hyperliquid", *METADATA, answer)).candles("BTC", timeframe, 110, NOW)

    assert len(candles) == 110
    assert all(candle.closed_at <= NOW for candle in candles)
    assert candles[-1] == LAST_CANDLES[timeframe.minutes]


@pytest.mark.parametrize(
    ("timeframe", "answer"), [(Timeframe(15), "candles_btc_15m"), (LONG_TIMEFRAME, "candles_btc_4h")]
)
def test_the_request_asks_the_candles_of_the_asset_over_the_count_and_one_more(
    timeframe: Timeframe, answer: str
) -> None:
    service = RecordedService("hyperliquid", *METADATA, answer)

    market(service).candles("BTC", timeframe, 110, NOW)

    assert service.received[-1] == (
        "POST",
        INFO_URL,
        {"type": "candleSnapshot", "req": CANDLE_REQUESTS[timeframe.minutes]},
    )


def test_the_recorded_contexts_give_the_current_values_of_the_asset() -> None:
    service = RecordedService("hyperliquid", *METADATA, "meta_and_asset_ctxs")

    snapshot = market(service).snapshot("BTC")

    assert snapshot == MarketSnapshot(
        price=Decimal("61041.5"),
        mid=Decimal("61079.5"),
        open_interest=Decimal("55.4016"),
        funding_rate=Decimal("0.0000125"),
    )
    assert service.received[-1] == ("POST", INFO_URL, {"type": "metaAndAssetCtxs"})


def test_the_recorded_daily_candle_gives_the_previous_utc_day() -> None:
    service = RecordedService("hyperliquid", *METADATA, "candles_btc_previous_day")

    day = market(service).previous_day("BTC", NOW)

    assert day == DailyRange(high=Decimal("63044.0"), low=Decimal("56371.0"), close=Decimal("58828.0"))
    assert service.received[-1] == (
        "POST",
        INFO_URL,
        {
            "type": "candleSnapshot",
            "req": {"coin": "BTC", "interval": "1d", "startTime": 1795132800000, "endTime": 1795219199999},
        },
    )


def test_a_rate_limit_is_a_transient_unavailability_of_the_market_data() -> None:
    service = RecordedService("hyperliquid", error="rate_limited_429")

    with pytest.raises(SourceUnavailableError) as raised:
        market(service).snapshot("BTC")

    assert (str(raised.value), raised.value.permanent) == (f"fonte non raggiungibile: {MARKET_DATA}", False)
