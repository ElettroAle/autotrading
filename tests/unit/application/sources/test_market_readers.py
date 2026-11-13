import json
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from autotrading.application.sources.errors import AssetRequiredError
from autotrading.application.sources.ports import SourceRequest
from autotrading.application.sources.read_indicators import ReadIndicatorsUseCase, text_of
from autotrading.application.sources.read_pivots import ReadPivotsUseCase
from autotrading.domain.sources.errors import InsufficientHistoryError
from autotrading.domain.sources.indicator_series import WARM_UP
from autotrading.domain.sources.market_snapshot import MarketSnapshot
from autotrading.domain.sources.timeframe import Timeframe
from tests.fakes.market_data import DEFAULT_CLOSES, FakeMarketDataAdapter

NOW = datetime(2026, 11, 12, 10, 7, tzinfo=UTC)


def command(asset: str | None = "BTC", length: int = 10) -> SourceRequest:
    return SourceRequest(uuid4(), asset, {"lunghezza_serie": length}, NOW)


def priced(market: FakeMarketDataAdapter, price: str) -> FakeMarketDataAdapter:
    market.snapshots["BTC"] = MarketSnapshot(Decimal(price), Decimal(price), Decimal(1), Decimal(0))
    return market


# Indicators


def test_the_indicators_ask_the_two_timeframes_with_the_history_their_averages_need() -> None:
    market = FakeMarketDataAdapter()

    ReadIndicatorsUseCase(market, 15).execute(command(length=7))

    assert market.requests == [("BTC", "15m", 7 + WARM_UP), ("BTC", "4h", 7 + WARM_UP)]


def test_the_short_timeframe_follows_the_cycle_interval() -> None:
    market = FakeMarketDataAdapter()

    [value] = ReadIndicatorsUseCase(market, 60).execute(command())

    assert value.values["breve.timeframe"] == "1h"
    assert value.values["lungo.timeframe"] == "4h"
    assert market.requests[0][1] == "1h"


def test_the_short_timeframe_is_chosen_among_the_intervals_the_market_publishes() -> None:
    market = FakeMarketDataAdapter(published=(Timeframe(1), Timeframe(5), Timeframe(240)))

    [value] = ReadIndicatorsUseCase(market, 15).execute(command())

    assert value.values["breve.timeframe"] == "5m"
    assert market.requests[0][1] == "5m"


def test_the_data_refers_to_the_close_of_the_last_short_candle() -> None:
    [value] = ReadIndicatorsUseCase(FakeMarketDataAdapter(), 15).execute(command())

    assert value.reference_at == datetime(2026, 11, 12, 10, 0, tzinfo=UTC)


def test_every_indicator_has_its_current_value_and_its_series() -> None:
    [value] = ReadIndicatorsUseCase(FakeMarketDataAdapter(), 15).execute(command(length=4))
    values = value.values

    series = json.loads(values["breve.volume.serie"])
    assert len(series) == 4
    assert Decimal(str(series[-1])) == Decimal(values["breve.volume"])
    assert "breve.EMA50" not in values
    assert {"lungo.EMA50", "lungo.MA50.serie"} <= set(values)
    assert values["prezzo"] == "100"
    assert values["mid_price"] == "100.5"


def test_a_market_too_short_makes_the_indicators_insufficient() -> None:
    market = FakeMarketDataAdapter(closes={("BTC", "15m"): DEFAULT_CLOSES[:20]})

    with pytest.raises(InsufficientHistoryError):
        ReadIndicatorsUseCase(market, 15).execute(command())


@pytest.mark.parametrize(
    ("value", "text"),
    [
        (Decimal("74572.123456789"), "74572.123"),
        (Decimal("0.0000123456789"), "0.000012345679"),
        (Decimal("123456789.5"), "123456790"),
        (Decimal("100.500"), "100.5"),
        (Decimal(0), "0"),
    ],
)
def test_a_value_keeps_8_significant_digits_without_exponent(value: Decimal, text: str) -> None:
    assert text_of(value) == text


# Pivots


def test_the_pivots_give_the_five_levels_and_the_price() -> None:
    [value] = ReadPivotsUseCase(priced(FakeMarketDataAdapter(), "105")).execute(command())

    assert {name: value.values[name] for name in ("S2", "S1", "PP", "R1", "R2", "prezzo")} == {
        "S2": "80",
        "S1": "90",
        "PP": "100",
        "R1": "110",
        "R2": "120",
        "prezzo": "105",
    }
    assert value.reference_at == NOW


def test_a_price_between_the_levels_has_both_nearest_with_their_distance() -> None:
    [value] = ReadPivotsUseCase(priced(FakeMarketDataAdapter(), "105")).execute(command())

    assert {key: value.values[key] for key in value.values if "vicin" in key or "distanza" in key} == {
        "resistenza_vicina": "R1",
        "distanza_resistenza_percentuale": "4.76",
        "supporto_vicino": "PP",
        "distanza_supporto_percentuale": "4.76",
    }
    assert value.values["posizione_rispetto_al_pp"] == "sopra"


def test_a_price_below_the_last_support_declares_no_support() -> None:
    [value] = ReadPivotsUseCase(priced(FakeMarketDataAdapter(), "75")).execute(command())

    assert value.values["supporto_vicino"] == "nessun supporto sotto il prezzo"
    assert "distanza_supporto_percentuale" not in value.values
    assert (value.values["resistenza_vicina"], value.values["posizione_rispetto_al_pp"]) == ("S2", "sotto")


@pytest.mark.parametrize(
    "reader", [ReadIndicatorsUseCase(FakeMarketDataAdapter(), 15), ReadPivotsUseCase(FakeMarketDataAdapter())]
)
def test_the_market_sources_need_an_asset(reader: ReadIndicatorsUseCase | ReadPivotsUseCase) -> None:
    with pytest.raises(AssetRequiredError):
        reader.execute(command(asset=None))
