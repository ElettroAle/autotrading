from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from autotrading.application.sources.errors import AssetRequiredError, SourceUnavailableError
from autotrading.application.sources.ports import SourceRequest
from autotrading.application.sources.read_volumes import ReadVolumesUseCase
from autotrading.domain.sources.source_sample import SourceValue
from autotrading.domain.sources.volume_snapshot import BookLevel, VolumeSnapshot
from tests.fakes.volumes import FakeVolumesAdapter, VolumesAsked

NOW = datetime(2026, 11, 20, 10, 0, tzinfo=UTC)
SNAPSHOT = VolumeSnapshot(
    Decimal("2500000.7"),
    Decimal(300),
    Decimal(200),
    (BookLevel(Decimal(99), Decimal(1)),),
    (BookLevel(Decimal(101), Decimal(3)),),
)


def request(asset: str | None = "BTC") -> SourceRequest:
    return SourceRequest(uuid4(), asset, {}, NOW)


def test_asks_the_exchange_for_the_asset_over_the_interval_of_the_cycle() -> None:
    exchange = FakeVolumesAdapter("Borsa", published={"BTC": SNAPSHOT})

    ReadVolumesUseCase(exchange, 30).execute(request())

    assert exchange.asked == [VolumesAsked("BTC", 30)]


def test_the_volumes_of_the_asset_refer_to_the_instant_of_the_reading() -> None:
    exchange = FakeVolumesAdapter("Borsa", published={"BTC": SNAPSHOT})

    values = ReadVolumesUseCase(exchange, 30).execute(request())

    assert values == (
        SourceValue(
            NOW,
            {
                "volume_24h_usd": "2500001",
                "rapporto_taker_buy_sell": "1.5000",
                "squilibrio_order_book_1_percento": "0.2463",
            },
        ),
    )


def test_an_asset_the_exchange_does_not_list_is_declared_with_the_name_of_the_adapter() -> None:
    values = ReadVolumesUseCase(FakeVolumesAdapter("Borsa"), 30).execute(request("PURR"))

    assert values == (SourceValue(NOW, {"nota": "non quotato su Borsa"}),)


def test_an_exchange_out_of_reach_leaves_the_source_unavailable() -> None:
    with pytest.raises(SourceUnavailableError):
        ReadVolumesUseCase(FakeVolumesAdapter("Borsa", reachable=False), 30).execute(request())


def test_the_volumes_are_read_for_an_asset() -> None:
    with pytest.raises(AssetRequiredError):
        ReadVolumesUseCase(FakeVolumesAdapter("Borsa"), 30).execute(request(None))
