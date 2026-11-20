from decimal import Decimal

import pytest

from autotrading.domain.sources.errors import InvalidVolumeSnapshotError
from autotrading.domain.sources.volume_figures import VolumeFigures
from autotrading.domain.sources.volume_snapshot import BookLevel, VolumeSnapshot

# The best bid at 99500 and the best ask at 100500 put the mid price at 100000, the band from 99000 to 101000.
BIDS = (
    BookLevel(Decimal(99500), Decimal(10)),
    BookLevel(Decimal(99000), Decimal(1)),
    BookLevel(Decimal(98999), Decimal(9)),
)
ASKS = (
    BookLevel(Decimal(100500), Decimal(6)),
    BookLevel(Decimal(101000), Decimal(1)),
    BookLevel(Decimal(101001), Decimal(9)),
)


def snapshot(
    taker_buy: Decimal = Decimal(6), taker_sell: Decimal = Decimal(4), bids: tuple[BookLevel, ...] = BIDS
) -> VolumeSnapshot:
    return VolumeSnapshot(Decimal(1000), taker_buy, taker_sell, bids, ASKS)


def test_the_taker_ratio_is_the_aggressive_buys_over_the_aggressive_sells() -> None:
    assert snapshot().taker_ratio == Decimal("1.5")


def test_without_aggressive_sells_the_taker_ratio_is_not_known() -> None:
    assert snapshot(taker_sell=Decimal(0)).taker_ratio is None


def test_the_imbalance_is_the_share_of_the_bids_within_one_percent_of_the_mid_price() -> None:
    bids = Decimal(995000) + Decimal(99000)
    asks = Decimal(603000) + Decimal(101000)

    assert snapshot().book_imbalance == bids / (bids + asks)


def test_without_bids_the_imbalance_is_not_known() -> None:
    assert snapshot(bids=()).book_imbalance is None


def test_a_book_with_no_value_within_the_band_has_no_imbalance() -> None:
    empty = (BookLevel(Decimal(99500), Decimal(0)),)
    assert (
        VolumeSnapshot(
            Decimal(1), Decimal(1), Decimal(1), empty, (BookLevel(Decimal(100500), Decimal(0)),)
        ).book_imbalance
        is None
    )


def test_the_figures_carry_the_volume_the_ratio_and_the_imbalance() -> None:
    reading = snapshot()

    assert reading.figures() == VolumeFigures(Decimal(1000), reading.taker_ratio, reading.book_imbalance)


@pytest.mark.parametrize(
    ("volume", "taker_buy", "taker_sell"),
    [
        (Decimal(-1), Decimal(1), Decimal(1)),
        (Decimal(1), Decimal(-1), Decimal(1)),
        (Decimal(1), Decimal(1), Decimal(-1)),
    ],
)
def test_a_negative_volume_is_refused(volume: Decimal, taker_buy: Decimal, taker_sell: Decimal) -> None:
    with pytest.raises(InvalidVolumeSnapshotError):
        VolumeSnapshot(volume, taker_buy, taker_sell, BIDS, ASKS)


@pytest.mark.parametrize(("price", "quantity"), [(Decimal(0), Decimal(1)), (Decimal(1), Decimal(-1))])
def test_a_level_of_the_book_without_a_price_or_with_a_negative_quantity_is_refused(
    price: Decimal, quantity: Decimal
) -> None:
    with pytest.raises(InvalidVolumeSnapshotError):
        BookLevel(price, quantity)
