"""The market data adapter against the public info endpoint of the Hyperliquid testnet, without credentials: run by
hand with -m sources."""

from datetime import UTC, datetime, timedelta

import pytest

from autotrading.adapters.outbound.hyperliquid.market_data import HyperliquidMarketDataAdapter
from autotrading.domain.sources.timeframe import LONG_TIMEFRAME, Timeframe

pytestmark = pytest.mark.sources

MARKET = HyperliquidMarketDataAdapter.for_network(testnet=True)


@pytest.mark.parametrize("timeframe", [Timeframe(15), LONG_TIMEFRAME])
def test_the_testnet_gives_the_closed_candles_asked(timeframe: Timeframe) -> None:
    now = datetime.now(UTC)

    candles = MARKET.candles("BTC", timeframe, 110, now)

    assert len(candles) == 110
    assert all(candle.closed_at <= now for candle in candles)
    assert now - candles[-1].closed_at < timedelta(minutes=timeframe.minutes)


def test_the_testnet_gives_the_current_values_of_the_asset() -> None:
    snapshot = MARKET.snapshot("BTC")

    assert snapshot.price > 0
    assert snapshot.mid > 0
    assert snapshot.open_interest > 0


def test_the_testnet_gives_the_previous_utc_day() -> None:
    day = MARKET.previous_day("BTC", datetime.now(UTC))

    assert day.low <= day.close <= day.high
