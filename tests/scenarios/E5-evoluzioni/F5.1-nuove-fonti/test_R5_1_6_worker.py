"""R5.1.6: the periods, horizons and windows of the market sources are lists the flow chooses; every value produces its
own values in the context, named after it, an empty list switches them off and reads nothing for them, and a value the
history of the market cannot give is declared among the missing data while the others arrive. On the cycle the worker
composes, with the fake market of the exchange (ADR parametri-delle-fonti-come-liste-libere).
"""

import re
from datetime import datetime
from decimal import Decimal

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.support.flow_cycles import FlowCycles
from tests.support.steps import quoted

scenarios(
    "E5-evoluzioni/F5.1-nuove-fonti/R5.1.6-parametri-a-lista-per-le-fonti-di-mercato/worker/R5.1.6-parametri-a-lista-per-le-fonti-di-mercato.feature"
)

USER = "anna"
FLOW = "liste"
ASSET = "BTC"
INDICATORS = "indicatori"
PIVOTS = "pivot"
FORECAST = "forecast"
DAY = "1d"
LONG = "4h"
SHORT = "15m"
TREND = "tendenza."
MISSING = "dati_mancanti"
LIST = r"\[[^\]]*\]"
AVERAGE_OR_RSI = re.compile(r"^(breve|lungo)\.(EMA|MA|RSI)\d+$")
PIVOT_LEVELS = ("PP", "R1", "R2", "S1", "S2")
FIBONACCI_LEVELS = ("23.6%", "38.2%", "50%", "61.8%", "78.6%")
GANN_ANGLES = ("1x1", "1x2", "2x1")
# Every candle of the fake market without a known range spans one unit on each side of its close.
SPREAD = Decimal(1)


@pytest.fixture
def flow_cycles() -> FlowCycles:
    return FlowCycles()


def numbers(text: str) -> tuple[int, ...]:
    """The numbers of a list as the scenario writes it: "[10, 200]", "[]"."""
    inside = text.strip().removeprefix("[").removesuffix("]")
    return tuple(int(piece) for piece in inside.split(",") if piece.strip())


def number(text: str) -> Decimal:
    return Decimal(text.replace(",", "."))


def rising_closes(count: int) -> list[Decimal]:
    return [Decimal(100) + index for index in range(count)]


def change(closes: list[Decimal], days: int) -> Decimal:
    return round((closes[-1] / closes[-1 - days] - 1) * 100, 4)


def flow_with(flow_cycles: FlowCycles, source: str, **parameters: tuple[int, ...]) -> None:
    """The flow of the scenario, with the source and its lists."""
    flow_cycles.add_flow(USER, FLOW, assets=(ASSET,), sources=(source,))
    flow_cycles.set_source_parameters(FLOW, source, **parameters)


def values_of(flow_cycles: FlowCycles, source: str) -> dict[str, str]:
    [values] = flow_cycles.sources_in_context(source, ASSET)
    return values


def daily_closes(flow_cycles: FlowCycles) -> list[Decimal]:
    return list(flow_cycles.market.closes[ASSET, DAY])


# Given


@given(
    parsers.re(
        rf"^un flusso con la fonte indicatori, medie_periodi (?P<averages>{LIST}) e rsi_periodi (?P<rsi>{LIST})$"
    )
)
def averages_and_rsi(flow_cycles: FlowCycles, averages: str, rsi: str) -> None:
    flow_with(flow_cycles, INDICATORS, medie_periodi=numbers(averages), rsi_periodi=numbers(rsi))


@given(parsers.re(rf"^tendenza_giorni (?P<trend>{LIST}) e canale_giorni (?P<channel>{LIST})$"))
def trend_and_channel(flow_cycles: FlowCycles, trend: str, channel: str) -> None:
    flow_with(flow_cycles, INDICATORS, tendenza_giorni=numbers(trend), canale_giorni=numbers(channel))


@given(parsers.re(rf"^tendenza_giorni (?P<trend>{LIST})$"))
def trend_only(flow_cycles: FlowCycles, trend: str) -> None:
    flow_with(flow_cycles, INDICATORS, tendenza_giorni=numbers(trend))


@given(parsers.re(rf"^canale_giorni (?P<channel>{LIST})$"))
def channel_only(flow_cycles: FlowCycles, channel: str) -> None:
    flow_with(flow_cycles, INDICATORS, canale_giorni=numbers(channel))


@given(parsers.re(rf"^volume_relativo_candele (?P<windows>{LIST})$"))
def relative_volume(flow_cycles: FlowCycles, windows: str) -> None:
    flow_with(flow_cycles, INDICATORS, volume_relativo_candele=numbers(windows))


@given(
    parsers.re(
        rf"^fibonacci_candele (?P<fibonacci>{LIST}), gann_candele (?P<gann>{LIST}) e ciclo_candele (?P<cycle>{LIST})$"
    )
)
def extended_windows(flow_cycles: FlowCycles, fibonacci: str, gann: str, cycle: str) -> None:
    flow_with(
        flow_cycles,
        INDICATORS,
        fibonacci_candele=numbers(fibonacci),
        gann_candele=numbers(gann),
        ciclo_candele=numbers(cycle),
    )
    # Closes that rise and fall, so that every window has its own extremes.
    flow_cycles.market.closes[ASSET, LONG] = [Decimal(50000) + Decimal((index * 37) % 101) * 10 for index in range(400)]


@given(parsers.re(rf"^orizzonti_minuti (?P<horizons>{LIST})$"))
def forecast_horizons(flow_cycles: FlowCycles, horizons: str) -> None:
    flow_with(flow_cycles, FORECAST, orizzonti_minuti=numbers(horizons))


@given(parsers.re(rf"^pivot_giorni (?P<days>{LIST})$"))
def pivot_days(flow_cycles: FlowCycles, days: str) -> None:
    flow_with(flow_cycles, PIVOTS, pivot_giorni=numbers(days))
    flow_cycles.market.closes[ASSET, DAY] = rising_closes(30)


@given(quoted("la chiusura giornaliera di {days} giorni fa a {before} e l'ultima a {last}"))
def known_closes(flow_cycles: FlowCycles, days: str, before: str, last: str) -> None:
    closes = [Decimal(52000)] * (int(days) + 1)
    closes[0], closes[-1] = number(before), number(last)
    flow_cycles.market.closes[ASSET, DAY] = closes


@given(quoted("venti giornate chiuse con massimo {high} e minimo {low}"))
def twenty_days(flow_cycles: FlowCycles, high: str, low: str) -> None:
    middle = (number(high) + number(low)) / 2
    previous = [number(low), number(high), *[middle] * 18]
    # The last close stands above the channel: only the twenty days before it make it.
    flow_cycles.market.closes[ASSET, DAY] = [*previous, number(high) * 2]


@given(
    quoted("l'ultima candela chiusa del timeframe lungo con volume {last} e le {count} precedenti con media {average}")
)
def known_volumes(flow_cycles: FlowCycles, last: str, count: str, average: str) -> None:
    # Volumes around the average, and an older one far from it: only the mean of the window is the one of the scenario.
    previous = [number(average) + (1 if index % 2 else -1) for index in range(int(count))]
    flow_cycles.market.volumes[ASSET, LONG] = [Decimal(999), *previous, number(last)]


@given(quoted("la giornata UTC corrente non ancora chiusa"))
def day_still_open(flow_cycles: FlowCycles) -> None:
    now = flow_cycles.clock.now()
    assert now != now.replace(hour=0, minute=0, second=0, microsecond=0)
    flow_cycles.market.closes[ASSET, DAY] = rising_closes(61)


@given(
    parsers.re(
        rf"^tendenza_giorni (?P<trend>{LIST}) e un adapter del mercato che dà solo (?P<count>\d+) giornate chiuse$"
    )
)
def short_daily_history(flow_cycles: FlowCycles, trend: str, count: str) -> None:
    flow_with(flow_cycles, INDICATORS, tendenza_giorni=numbers(trend))
    flow_cycles.market.closes[ASSET, DAY] = rising_closes(int(count))


# When


@when("parte un ciclo")
def a_cycle_starts(flow_cycles: FlowCycles) -> None:
    flow_cycles.run(FLOW)


# Then


@then("il contesto contiene EMA10, EMA200, MA10, MA200 e RSI21, e nessun'altra media o RSI")
def chosen_averages_and_rsi(flow_cycles: FlowCycles) -> None:
    values = values_of(flow_cycles, INDICATORS)
    expected = {
        f"{side}.{name}" for side in ("breve", "lungo") for name in ("EMA10", "EMA200", "MA10", "MA200", "RSI21")
    }
    assert {key for key in values if AVERAGE_OR_RSI.match(key)} == expected


@then("il contesto contiene la variazione a 3 e a 90 giorni e il canale a 10 giorni")
def chosen_trend(flow_cycles: FlowCycles) -> None:
    values = values_of(flow_cycles, INDICATORS)
    trend = {key.removeprefix(TREND) for key in values if key.startswith(TREND)}
    assert {name for name in trend if name.startswith("variazione_")} == {"variazione_3g", "variazione_90g"}
    assert {name for name in trend if name.endswith("0g") and not name.startswith("variazione_")} == {
        "massimo_10g",
        "minimo_10g",
        "punto_medio_10g",
    }


@then(quoted("la variazione a {days} giorni è {expected}"))
def change_over(flow_cycles: FlowCycles, days: str, expected: str) -> None:
    assert number(values_of(flow_cycles, INDICATORS)[f"{TREND}variazione_{days}g"]) == number(expected)


@then(quoted("il contesto contiene per il canale a {days} giorni massimo {high}, minimo {low} e punto medio {middle}"))
def channel(flow_cycles: FlowCycles, days: str, high: str, low: str, middle: str) -> None:
    values = values_of(flow_cycles, INDICATORS)
    assert number(values[f"{TREND}massimo_{days}g"]) == number(high)
    assert number(values[f"{TREND}minimo_{days}g"]) == number(low)
    assert number(values[f"{TREND}punto_medio_{days}g"]) == number(middle)


@then(quoted("il contesto contiene il volume relativo a {count} candele del timeframe lungo uguale a {expected}"))
def long_relative_volume(flow_cycles: FlowCycles, count: str, expected: str) -> None:
    assert number(values_of(flow_cycles, INDICATORS)[f"lungo.volume_relativo{count}"]) == number(expected)


@then("quello del timeframe breve calcolato allo stesso modo sulle sue candele")
def short_relative_volume(flow_cycles: FlowCycles) -> None:
    values = values_of(flow_cycles, INDICATORS)
    [window] = [
        int(key.removeprefix("breve.volume_relativo")) for key in values if key.startswith("breve.volume_relativo")
    ]
    # The fake market gives a candle without a known volume the volume 5 plus its position among those read.
    [read] = [request[2] for request in flow_cycles.market.requests if request[1] == SHORT]
    volumes = [Decimal(5) + index for index in range(read)]
    expected = volumes[-1] / (sum(volumes[-1 - window : -1], Decimal(0)) / window)
    assert round(number(values[f"breve.volume_relativo{window}"]), 6) == round(expected, 6)


@then(
    "il contesto contiene i livelli di Fibonacci su 100 e su 200 candele, gli angoli di Gann su 100 e il ciclo "
    "dominante su 200"
)
def extended_values(flow_cycles: FlowCycles) -> None:
    values = values_of(flow_cycles, INDICATORS)
    closes = flow_cycles.market.closes[ASSET, LONG]
    for window in (100, 200):
        assert number(values[f"lungo.fibonacci{window}.massimo"]) == max(closes[-window:]) + SPREAD
        assert all(f"lungo.fibonacci{window}.{level}" in values for level in FIBONACCI_LEVELS)
    assert all(f"lungo.gann100.{angle}" in values for angle in GANN_ANGLES)
    assert 4 <= int(values["lungo.ciclo200.periodo_candele"]) <= 100
    assert not [key for key in values if key.startswith(("lungo.gann200", "lungo.ciclo100"))]


@then("il contesto contiene il forecast a 15 minuti, 4 ore e 1 giorno")
def free_horizons(flow_cycles: FlowCycles) -> None:
    values = values_of(flow_cycles, FORECAST)
    predicted = {key.removeprefix("prezzo_previsto_") for key in values if key.startswith("prezzo_previsto_")}
    assert predicted == {"15 minuti", "4 ore", "1 giorno"}


@then("il contesto contiene i pivot del giorno precedente e dei 7 giorni precedenti")
def pivots_over_periods(flow_cycles: FlowCycles) -> None:
    values = values_of(flow_cycles, PIVOTS)
    closes = daily_closes(flow_cycles)
    for days in (1, 7):
        window = closes[-days:]
        pivot = (max(window) + SPREAD + min(window) - SPREAD + window[-1]) / 3
        assert round(number(values[f"pivot_{days}g.PP"]), 4) == round(pivot, 4)
        assert all(f"pivot_{days}g.{level}" in values for level in PIVOT_LEVELS)


@then("il contesto non contiene valori di tendenza e la fonte non legge candele giornaliere")
def no_trend(flow_cycles: FlowCycles) -> None:
    values = values_of(flow_cycles, INDICATORS)
    assert values
    assert not [key for key in values if key.startswith(TREND)]
    assert flow_cycles.market.requests
    assert not [request for request in flow_cycles.market.requests if request[1] == DAY]


@then("variazione e canale usano come ultima chiusura quella della giornata precedente")
def last_close_of_the_previous_day(flow_cycles: FlowCycles) -> None:
    values = values_of(flow_cycles, INDICATORS)
    now = flow_cycles.clock.now()
    closes = daily_closes(flow_cycles)
    assert datetime.fromisoformat(values[f"{TREND}ultima_chiusura_istante"]) == now.replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    assert round(number(values[f"{TREND}variazione_7g"]), 4) == change(closes, 7)
    assert number(values[f"{TREND}massimo_20g"]) == max(closes[-21:-1])


@then(quoted("il contesto contiene la variazione a {days} giorni"))
def change_present(flow_cycles: FlowCycles, days: str) -> None:
    values = values_of(flow_cycles, INDICATORS)
    assert round(number(values[f"{TREND}variazione_{days}g"]), 4) == change(daily_closes(flow_cycles), int(days))


@then(quoted("la variazione a {days} giorni compare tra i dati mancanti"))
def change_missing(flow_cycles: FlowCycles, days: str) -> None:
    values = values_of(flow_cycles, INDICATORS)
    assert f"{TREND}variazione_{days}g" in values[MISSING]
    assert f"{TREND}variazione_{days}g" not in values
