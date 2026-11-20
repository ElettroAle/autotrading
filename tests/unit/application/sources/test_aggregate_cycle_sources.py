from collections.abc import Mapping
from dataclasses import dataclass

from autotrading.application.sources.aggregate_cycle_sources import AggregateCycleSourcesUseCase, AggregatedSource
from autotrading.domain.sources.volume_aggregate import AGGREGATE


@dataclass(frozen=True, slots=True)
class Datum:
    """A datum of the cycle as the flows hand it over: the source, the adapter, its weight, the asset and the values."""

    source: str
    adapter: str
    weight: int
    asset: str | None
    values: Mapping[str, str]


def volumes(adapter: str, weight: int, asset: str, figures: tuple[str, str, str]) -> Datum:
    """The volumes of an exchange: the volume of 24 hours, the taker ratio and the imbalance of the book."""
    keys = ("volume_24h_usd", "rapporto_taker_buy_sell", "squilibrio_order_book_1_percento")
    return Datum("volumi", adapter, weight, asset, dict(zip(keys, figures, strict=True)))


def test_the_volumes_are_grouped_by_asset_and_every_aggregate_of_the_domain_is_a_datum_of_the_context() -> None:
    data = (
        volumes("Borsa", 3, "BTC", ("300", "2.0000", "0.6000")),
        volumes("Mercato", 7, "BTC", ("100", "1.0000", "0.2000")),
        volumes("Borsa", 3, "ETH", ("50", "1.0000", "0.5000")),
    )

    aggregates = AggregateCycleSourcesUseCase().execute(data)

    assert aggregates == (
        AggregatedSource(
            "volumi",
            AGGREGATE,
            7,
            "BTC",
            {
                "volume_24h_usd": "400",
                "rapporto_taker_buy_sell": "1.7500",
                "squilibrio_order_book_1_percento": "0.5000",
            },
        ),
    )


def test_a_single_exchange_has_no_aggregate() -> None:
    assert AggregateCycleSourcesUseCase().execute((volumes("Borsa", 5, "BTC", ("300", "2.0000", "0.6000")),)) == ()


def test_an_exchange_that_does_not_list_the_asset_stays_out_of_its_aggregate() -> None:
    data = (
        volumes("Borsa", 5, "BTC", ("300", "2.0000", "0.6000")),
        Datum("volumi", "Mercato", 5, "BTC", {"nota": "non quotato su Mercato"}),
    )

    assert AggregateCycleSourcesUseCase().execute(data) == ()


def test_the_other_sources_have_no_aggregate() -> None:
    data = (
        Datum("sentiment", "Indice", 5, None, {"valore": "50"}),
        Datum("sentiment", "Altro indice", 5, None, {"valore": "60"}),
    )

    assert AggregateCycleSourcesUseCase().execute(data) == ()
