"""The price history adapter against the public candles of the Hyperliquid testnet, without credentials: run by hand
with -m sources."""

from datetime import UTC, datetime, timedelta

import pytest

from autotrading.adapters.outbound.hyperliquid.market_data import HyperliquidPriceHistoryAdapter
from autotrading.domain.sources.price_forecast import history_of

pytestmark = pytest.mark.sources


@pytest.mark.parametrize("days", [1, 7, 90])
def test_the_testnet_answers_with_a_recent_history_of_the_requested_depth(days: int) -> None:
    now = datetime.now(UTC)

    history = history_of(HyperliquidPriceHistoryAdapter.for_network(testnet=True).history("BTC", days, now), days, now)

    assert now - history.points[-1].at < timedelta(hours=1)
    assert history.points[0].at - (now - timedelta(days=days)) < timedelta(hours=1)
    assert history.last_price > 0


def test_the_testnet_answers_with_the_current_price() -> None:
    assert HyperliquidPriceHistoryAdapter.for_network(testnet=True).current_price("BTC") > 0
