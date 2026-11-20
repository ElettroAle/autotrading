"""The Binance adapter of the volumes against the real public market data, without any key: run by hand with -m
sources (ADR fonte-volumi-con-adapter-binance)."""

import pytest

from autotrading.adapters.outbound.binance.composition import binance_adapters
from autotrading.domain.sources.volume_snapshot import UnlistedAsset, VolumeSnapshot

pytestmark = pytest.mark.sources


def test_the_market_data_give_the_volumes_and_the_book_of_a_listed_asset() -> None:
    reading = binance_adapters().snapshot("BTC", 15)

    assert isinstance(reading, VolumeSnapshot)
    assert reading.volume_24h_usd > 0
    assert reading.taker_buy + reading.taker_sell > 0
    assert reading.bids
    assert reading.asks
    assert reading.book_imbalance is not None


def test_an_asset_binance_does_not_list_is_declared_not_listed() -> None:
    assert binance_adapters().snapshot("ZZZNOTLISTED", 15) == UnlistedAsset("ZZZNOTLISTED")
