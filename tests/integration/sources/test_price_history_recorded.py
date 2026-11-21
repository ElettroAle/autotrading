"""The price history adapter against the public candles of the Hyperliquid testnet as the info endpoint answered them,
recorded live on 21 November 2026 at 20:09 UTC through the official SDK, without credentials (ADR
fonti-provate-su-risposte-registrate).

- Every answer: POST https://api.hyperliquid-testnet.xyz/info, the body of the request in its recording
- meta: the perpetual markets the SDK reads before every client
- 429: the rate limit, https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/rate-limits-and-user-limits
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from hyperliquid.utils.constants import TESTNET_API_URL

from autotrading.adapters.outbound.hyperliquid.market_data import HyperliquidPriceHistoryAdapter
from autotrading.application.sources.errors import SourceUnavailableError
from autotrading.domain.sources.forecast import FORECAST
from autotrading.domain.sources.price_forecast import PricePoint, history_of
from tests.support.recorded_answers import RecordedInfoSdk, RecordedService

pytestmark = pytest.mark.integration

NOW = datetime(2026, 11, 21, 20, 9, tzinfo=UTC)
NOW_MS = 1795291740000
METADATA = ("meta",)
INFO_URL = f"{TESTNET_API_URL}/info"
LAST_PRICE = Decimal("61082.0")
# The candles of each depth: the finest interval the exchange keeps, the close of the first one, its count.
DEPTHS = {
    1: ("1m", datetime(2026, 11, 20, 20, 9, 59, 999000, tzinfo=UTC), Decimal("57059.0"), 1441),
    7: ("3m", datetime(2026, 11, 14, 20, 11, 59, 999000, tzinfo=UTC), Decimal("65065.0"), 3361),
    90: ("30m", datetime(2026, 8, 23, 20, 29, 59, 999000, tzinfo=UTC), Decimal("78690.0"), 4321),
}


def prices(service: RecordedService) -> HyperliquidPriceHistoryAdapter:
    return HyperliquidPriceHistoryAdapter(TESTNET_API_URL, RecordedInfoSdk(service))


@pytest.mark.parametrize("days", sorted(DEPTHS))
def test_the_recorded_candles_give_the_history_of_the_requested_depth_up_to_now(days: int) -> None:
    _, first_close, first_price, count = DEPTHS[days]
    service = RecordedService("hyperliquid", *METADATA, f"history_btc_{days}d")

    history = history_of(prices(service).history("BTC", days, NOW), days, NOW)

    assert len(history.points) == count
    assert history.points[0] == PricePoint(first_close, first_price)
    assert history.points[-1] == PricePoint(NOW, LAST_PRICE)
    assert history.last_price == LAST_PRICE


@pytest.mark.parametrize("days", sorted(DEPTHS))
def test_one_request_asks_the_finest_kept_candles_from_the_depth_to_now(days: int) -> None:
    interval = DEPTHS[days][0]
    service = RecordedService("hyperliquid", *METADATA, f"history_btc_{days}d")

    prices(service).history("BTC", days, NOW)

    start = int((NOW - timedelta(days=days)).timestamp() * 1000)
    request = {"coin": "BTC", "interval": interval, "startTime": start, "endTime": NOW_MS}
    assert service.received[-1] == ("POST", INFO_URL, {"type": "candleSnapshot", "req": request})


def test_the_recorded_mids_give_the_current_price() -> None:
    service = RecordedService("hyperliquid", *METADATA, "all_mids")

    assert prices(service).current_price("BTC") == Decimal("61079.5")
    assert service.received[-1] == ("POST", INFO_URL, {"type": "allMids", "dex": ""})


def test_a_rate_limit_is_a_transient_unavailability_of_the_forecast() -> None:
    service = RecordedService("hyperliquid", error="rate_limited_429")

    with pytest.raises(SourceUnavailableError) as raised:
        prices(service).current_price("BTC")

    assert (str(raised.value), raised.value.permanent) == (f"fonte non raggiungibile: {FORECAST.name}", False)
