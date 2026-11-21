"""The Binance adapter of the volumes against the answers of the real public market data, recorded live on 21 November
2026 (ADR fonti-provate-su-risposte-registrate, ADR fonte-volumi-con-adapter-binance).

- 24 hours: https://data-api.binance.vision/api/v3/ticker/24hr?symbol=BTCUSDT
- Candles of the interval: https://data-api.binance.vision/api/v3/klines?symbol=BTCUSDT&interval=1m&limit=15
- Book: https://data-api.binance.vision/api/v3/depth?symbol=BTCUSDT&limit=1000
- Not listed: https://data-api.binance.vision/api/v3/ticker/24hr?symbol=ZZZNOTLISTEDUSDT, 400 with code -1121
- 429: the rate limit, in the error format of the documentation of Binance
"""

from decimal import Decimal

import pytest

from autotrading.adapters.outbound.binance.volumes import BINANCE_URL, BinanceVolumesAdapter
from autotrading.application.sources.errors import SourceUnavailableError
from autotrading.domain.sources.volume_snapshot import BookLevel, UnlistedAsset, VolumeSnapshot
from tests.support.recorded_answers import RecordedHttpxService

pytestmark = pytest.mark.integration

LISTED = ("ticker_btcusdt", "klines_btcusdt", "depth_btcusdt")
TRADED = Decimal("6911680.05920590")
TAKER_BUY = Decimal("3024418.99109160")


def snapshot(service: RecordedHttpxService, asset: str = "BTC") -> VolumeSnapshot | UnlistedAsset:
    return BinanceVolumesAdapter(service.client(BINANCE_URL)).snapshot(asset, 15)


def test_the_recorded_market_data_give_the_volumes_and_the_book_of_a_listed_asset() -> None:
    reading = snapshot(RecordedHttpxService("binance", *LISTED))

    assert isinstance(reading, VolumeSnapshot)
    assert reading.volume_24h_usd == Decimal("3037836667.12951530")
    assert (reading.taker_buy, reading.taker_sell) == (TAKER_BUY, TRADED - TAKER_BUY)
    assert (len(reading.bids), len(reading.asks)) == (1000, 1000)
    assert reading.bids[0] == BookLevel(Decimal("60403.51000000"), Decimal("0.18621000"))
    assert reading.asks[0] == BookLevel(Decimal("60403.52000000"), Decimal("6.16383000"))
    assert reading.book_imbalance is not None


def test_the_requests_ask_the_day_the_minutes_of_the_interval_and_the_book_of_the_dollar_pair() -> None:
    service = RecordedHttpxService("binance", *LISTED)

    snapshot(service)

    assert [(request.url.path, dict(request.url.params)) for request in service.requests] == [
        ("/api/v3/ticker/24hr", {"symbol": "BTCUSDT"}),
        ("/api/v3/klines", {"symbol": "BTCUSDT", "interval": "1m", "limit": "15"}),
        ("/api/v3/depth", {"symbol": "BTCUSDT", "limit": "1000"}),
    ]
    assert {request.url.host for request in service.requests} == {"data-api.binance.vision"}


def test_an_asset_binance_does_not_list_is_declared_not_listed() -> None:
    assert snapshot(RecordedHttpxService("binance", "ticker_zzznotlistedusdt"), "ZZZNOTLISTED") == UnlistedAsset(
        "ZZZNOTLISTED"
    )


def test_a_rate_limit_is_a_transient_unavailability_of_the_source() -> None:
    with pytest.raises(SourceUnavailableError) as raised:
        snapshot(RecordedHttpxService("binance", error="rate_limited_429"))

    assert (str(raised.value), raised.value.permanent) == ("fonte non raggiungibile: Binance", False)
