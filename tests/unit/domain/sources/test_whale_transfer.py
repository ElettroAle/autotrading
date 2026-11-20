from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from autotrading.domain.sources.errors import InvalidWhaleTransferError
from autotrading.domain.sources.whale_transfer import WhaleTransfer, large_transfers

NOW = datetime(2026, 11, 20, 10, 0, tzinfo=UTC)


def transfer(minutes_ago: int, usd: str, asset: str = "BTC") -> WhaleTransfer:
    return WhaleTransfer(NOW - timedelta(minutes=minutes_ago), asset, Decimal(1), Decimal(usd), None, None)


def test_a_transfer_keeps_instant_asset_quantity_value_and_both_ends() -> None:
    moved = WhaleTransfer(NOW, "BTC", Decimal(500), Decimal("45000000"), "Binance", "wallet")

    assert (moved.at, moved.asset, moved.quantity, moved.usd_value, moved.origin, moved.destination) == (
        NOW,
        "BTC",
        Decimal(500),
        Decimal("45000000"),
        "Binance",
        "wallet",
    )


@pytest.mark.parametrize(
    ("at", "asset", "quantity", "usd_value"),
    [
        (NOW.replace(tzinfo=None), "BTC", Decimal(1), Decimal(1)),
        (NOW, " ", Decimal(1), Decimal(1)),
        (NOW, "BTC", Decimal(0), Decimal(1)),
        (NOW, "BTC", Decimal(1), Decimal(-1)),
    ],
)
def test_a_transfer_without_zone_asset_quantity_or_with_a_negative_value_is_refused(
    at: datetime, asset: str, quantity: Decimal, usd_value: Decimal
) -> None:
    with pytest.raises(InvalidWhaleTransferError, match=r"^trasferimento non valido$"):
        WhaleTransfer(at, asset, quantity, usd_value, None, None)


def test_the_description_names_both_ends_and_an_unknown_one_as_unlabelled() -> None:
    assert WhaleTransfer(NOW, "BTC", Decimal(1), Decimal(1), None, "Binance").description == (
        "da indirizzo non etichettato a Binance"
    )
    assert WhaleTransfer(NOW, "BTC", Decimal(1), Decimal(1), "Kraken", None).description == (
        "da Kraken a indirizzo non etichettato"
    )


def test_a_transfer_with_both_ends_unknown_has_no_description() -> None:
    assert WhaleTransfer(NOW, "BTC", Decimal(1), Decimal(1), None, None).description is None


def test_the_large_transfers_are_those_at_or_above_the_threshold_newest_first() -> None:
    chosen = large_transfers(
        [transfer(30, "2000000"), transfer(5, "1000000"), transfer(10, "999999.99"), transfer(1, "5000000", "ETH")],
        1_000_000,
    )

    assert [(item.asset, item.usd_value) for item in chosen] == [
        ("ETH", Decimal(5000000)),
        ("BTC", Decimal(1000000)),
        ("BTC", Decimal(2000000)),
    ]


def test_no_transfer_above_the_threshold_leaves_none() -> None:
    assert large_transfers([transfer(5, "10")], 1_000_000) == ()
