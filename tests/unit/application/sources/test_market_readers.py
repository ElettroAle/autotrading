import json
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from autotrading.application.sources.errors import AssetRequiredError
from autotrading.application.sources.ports import SourceRequest
from autotrading.application.sources.read_indicators import ReadIndicatorsUseCase, text_of
from autotrading.application.sources.read_pivots import ReadPivotsUseCase
from autotrading.domain.sources.errors import InsufficientHistoryError, TimeframeNotAvailableError
from autotrading.domain.sources.extended_indicators import ExtendedIndicatorChoice, fibonacci_levels
from autotrading.domain.sources.indicator_series import WARM_UP
from autotrading.domain.sources.long_trend import DAILY_TIMEFRAME, LongTrendChoice
from autotrading.domain.sources.market_snapshot import MarketSnapshot
from autotrading.domain.sources.source_parameter import SourceParameterValue
from autotrading.domain.sources.timeframe import LONG_TIMEFRAME, Timeframe
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
    assert {"breve.EMA50", "lungo.EMA50", "lungo.MA50.serie", "breve.RSI14.serie"} <= set(values)
    assert values["prezzo"] == "100"
    assert values["mid_price"] == "100.5"
    assert "dati_mancanti" not in values


def test_the_periods_chosen_are_read_on_both_timeframes_with_the_history_they_need() -> None:
    market = FakeMarketDataAdapter()

    [value] = ReadIndicatorsUseCase(market, 15).execute(extended(medie_periodi=(10, 200), rsi_periodi=(21,)))

    assert market.requests == [("BTC", "15m", 210), ("BTC", "4h", 210)]
    assert {key for key in value.values if key.startswith(("breve.EMA", "lungo.RSI")) and "serie" not in key} == {
        "breve.EMA10",
        "breve.EMA200",
        "lungo.RSI21",
    }


def test_a_period_the_history_cannot_give_is_missing_and_the_others_arrive() -> None:
    market = FakeMarketDataAdapter(closes={("BTC", "4h"): DEFAULT_CLOSES[:150]})

    [value] = ReadIndicatorsUseCase(market, 15).execute(extended(medie_periodi=(20, 200)))

    assert {"breve.EMA200", "lungo.EMA20"} <= set(value.values)
    assert "lungo.EMA200" not in value.values
    assert value.values["dati_mancanti"] == "lungo.EMA200, lungo.MA200: storico di 150 candele"


def test_the_relative_volume_of_each_window_is_given_on_both_timeframes() -> None:
    market = FakeMarketDataAdapter(volumes={("BTC", "4h"): [Decimal(100)] * 42 + [Decimal(300)]})

    [value] = ReadIndicatorsUseCase(market, 15).execute(extended(volume_relativo_candele=(42,)))

    assert value.values["lungo.volume_relativo42"] == "3"
    assert "breve.volume_relativo42" in value.values


def test_a_market_too_short_makes_the_indicators_insufficient() -> None:
    market = FakeMarketDataAdapter(closes={("BTC", "15m"): DEFAULT_CLOSES[:20]})

    with pytest.raises(InsufficientHistoryError):
        ReadIndicatorsUseCase(market, 15).execute(command())


def extended(asset: str = "BTC", **settings: SourceParameterValue) -> SourceRequest:
    return SourceRequest(uuid4(), asset, {"lunghezza_serie": 10, **settings}, NOW)


def test_without_extended_indicators_the_context_has_none_of_their_values() -> None:
    [value] = ReadIndicatorsUseCase(FakeMarketDataAdapter(), 15).execute(extended())

    assert not [key for key in value.values if key.startswith(("lungo.fibonacci", "lungo.gann", "lungo.ciclo"))]
    assert "lungo.nota_storico" not in value.values


def test_the_extended_indicators_read_their_longest_window_on_the_long_timeframe() -> None:
    market = FakeMarketDataAdapter()

    [value] = ReadIndicatorsUseCase(market, 15).execute(
        extended(fibonacci_candele=(100, 300), gann_candele=(300,), ciclo_candele=(300,))
    )

    long = market.candles("BTC", LONG_TIMEFRAME, 300, NOW)
    expected = ExtendedIndicatorChoice((300,), (300,), (300,)).values(long).values
    assert market.requests[1] == ("BTC", "4h", 300)
    assert value.values["lungo.fibonacci300.61.8%"] == text_of(fibonacci_levels(long)["61.8%"])
    assert value.values["lungo.fibonacci100.61.8%"] == text_of(fibonacci_levels(long[-100:])["61.8%"])
    assert value.values["lungo.gann300.perno"] == expected["gann300.perno"]
    assert value.values["lungo.ciclo300.periodo_candele"] == "9"
    assert "lungo.nota_storico" not in value.values


def test_a_long_history_shorter_than_a_window_is_declared() -> None:
    market = FakeMarketDataAdapter(closes={("BTC", "4h"): DEFAULT_CLOSES[:60]})

    [value] = ReadIndicatorsUseCase(market, 15).execute(extended(fibonacci_candele=(100,), medie_periodi=(20,)))

    assert value.values["lungo.nota_storico"] == "storico di 60 candele, meno delle 100 richieste"


def test_without_days_of_the_trend_no_daily_candle_is_read() -> None:
    market = FakeMarketDataAdapter()

    [value] = ReadIndicatorsUseCase(market, 15).execute(extended(tendenza_giorni=(), canale_giorni=()))

    assert [request[1] for request in market.requests] == ["15m", "4h"]
    assert not [key for key in value.values if key.startswith("tendenza.")]


def test_the_trend_reads_the_daily_candles_of_the_same_market_its_longest_value_needs() -> None:
    market = FakeMarketDataAdapter()

    [value] = ReadIndicatorsUseCase(market, 15).execute(extended(tendenza_giorni=(30,), canale_giorni=(60,)))

    daily = market.candles("BTC", DAILY_TIMEFRAME, 61, NOW)
    change = LongTrendChoice((30,), (60,)).values(daily).values["tendenza.variazione_30g"]
    assert isinstance(change, Decimal)
    assert ("BTC", "1d", 61) in market.requests
    assert value.values["tendenza.variazione_30g"] == text_of(change)
    assert value.values["tendenza.ultima_chiusura_istante"] == "2026-11-12T00:00:00+00:00"
    assert value.reference_at == datetime(2026, 11, 12, 10, 0, tzinfo=UTC)


def test_a_short_daily_history_declares_its_missing_values() -> None:
    market = FakeMarketDataAdapter(closes={("BTC", "1d"): DEFAULT_CLOSES[:20]})

    [value] = ReadIndicatorsUseCase(market, 15).execute(extended(tendenza_giorni=(7, 30), canale_giorni=(20,)))

    assert "tendenza.variazione_7g" in value.values
    assert value.values["dati_mancanti"] == "tendenza.variazione_30g, tendenza.canale_20g: storico di 20 giorni chiusi"


def test_a_market_without_daily_candles_cannot_give_the_long_trend() -> None:
    market = FakeMarketDataAdapter(published=(Timeframe(15), Timeframe(240)))

    with pytest.raises(TimeframeNotAvailableError):
        ReadIndicatorsUseCase(market, 15).execute(extended(tendenza_giorni=(7,)))


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


def previous_day(market: FakeMarketDataAdapter) -> FakeMarketDataAdapter:
    """The previous UTC day of the requirement: high 110, low 90, close 100 (R1.3.4), after a wider day."""
    market.closes["BTC", "1d"] = [Decimal(500), Decimal(100)]
    market.ranges["BTC", "1d"] = [(Decimal(510), Decimal(20)), (Decimal(110), Decimal(90))]
    return market


def pivots(*days: int) -> SourceRequest:
    return SourceRequest(uuid4(), "BTC", {"pivot_giorni": days}, NOW)


def test_the_pivots_give_the_five_levels_of_the_previous_day_and_the_price() -> None:
    market = priced(previous_day(FakeMarketDataAdapter()), "105")

    [value] = ReadPivotsUseCase(market).execute(pivots(1))

    assert {name: value.values[f"pivot_1g.{name}"] for name in ("S2", "S1", "PP", "R1", "R2")} == {
        "S2": "80",
        "S1": "90",
        "PP": "100",
        "R1": "110",
        "R2": "120",
    }
    assert value.values["prezzo"] == "105"
    assert value.reference_at == NOW
    assert market.requests == [("BTC", "1d", 1)]


def test_a_price_between_the_levels_has_both_nearest_with_their_distance() -> None:
    [value] = ReadPivotsUseCase(priced(previous_day(FakeMarketDataAdapter()), "105")).execute(pivots(1))

    assert {key: value.values[key] for key in value.values if "vicin" in key or "distanza" in key} == {
        "pivot_1g.resistenza_vicina": "R1",
        "pivot_1g.distanza_resistenza_percentuale": "4.76",
        "pivot_1g.supporto_vicino": "PP",
        "pivot_1g.distanza_supporto_percentuale": "4.76",
    }
    assert value.values["pivot_1g.posizione_rispetto_al_pp"] == "sopra"


def test_a_price_below_the_last_support_declares_no_support() -> None:
    [value] = ReadPivotsUseCase(priced(previous_day(FakeMarketDataAdapter()), "75")).execute(pivots(1))

    assert value.values["pivot_1g.supporto_vicino"] == "nessun supporto sotto il prezzo"
    assert "pivot_1g.distanza_supporto_percentuale" not in value.values
    assert (value.values["pivot_1g.resistenza_vicina"], value.values["pivot_1g.posizione_rispetto_al_pp"]) == (
        "S2",
        "sotto",
    )


def test_every_period_has_its_series_over_its_closed_days() -> None:
    market = priced(previous_day(FakeMarketDataAdapter()), "105")

    [value] = ReadPivotsUseCase(market).execute(pivots(1, 2))

    # Two days: high 510, low 20, close 100.
    assert value.values["pivot_2g.PP"] == "210"
    assert value.values["pivot_1g.PP"] == "100"
    assert market.requests == [("BTC", "1d", 2)]


def test_a_period_longer_than_the_history_is_missing_and_the_others_arrive() -> None:
    [value] = ReadPivotsUseCase(previous_day(FakeMarketDataAdapter())).execute(pivots(1, 7))

    assert "pivot_1g.PP" in value.values
    assert not [key for key in value.values if key.startswith("pivot_7g.")]
    assert value.values["dati_mancanti"] == "pivot_7g: storico di 2 giorni chiusi"


def test_no_period_reads_no_day_and_gives_the_price_alone() -> None:
    market = FakeMarketDataAdapter()

    [value] = ReadPivotsUseCase(market).execute(pivots())

    assert value.values == {"prezzo": "100"}
    assert market.requests == []


def test_the_default_period_is_the_previous_day() -> None:
    [value] = ReadPivotsUseCase(previous_day(FakeMarketDataAdapter())).execute(command())

    assert value.values["pivot_1g.PP"] == "100"


def test_a_market_without_daily_candles_cannot_give_the_pivots() -> None:
    market = FakeMarketDataAdapter(published=(Timeframe(15), Timeframe(240)))

    with pytest.raises(TimeframeNotAvailableError):
        ReadPivotsUseCase(market).execute(pivots(1))


@pytest.mark.parametrize(
    "reader", [ReadIndicatorsUseCase(FakeMarketDataAdapter(), 15), ReadPivotsUseCase(FakeMarketDataAdapter())]
)
def test_the_market_sources_need_an_asset(reader: ReadIndicatorsUseCase | ReadPivotsUseCase) -> None:
    with pytest.raises(AssetRequiredError):
        reader.execute(command(asset=None))
