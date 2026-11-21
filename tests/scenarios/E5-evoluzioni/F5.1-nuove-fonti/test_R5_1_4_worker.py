"""R5.1.4: Fibonacci retracements, Gann angles and the dominant cycle enter the context of the cycle as parameters of
the indicators source, computed on the closed 4-hour candles of the exchange; a history shorter than the candles asked
is declared and the indicators are computed on what there is. On the cycle the worker composes, with the fake market of
the exchange (ADR indicatori-estesi-nel-domain).
"""

from decimal import Decimal

import pytest
from pytest_bdd import given, scenarios, then, when

from tests.support.flow_cycles import FlowCycles
from tests.support.steps import quoted

scenarios("E5-evoluzioni/F5.1-nuove-fonti/R5.1.4-indicatori-estesi/worker/R5.1.4-indicatori-estesi.feature")

USER = "anna"
INDICATORS = "indicatori"
LONG = "4h"
EXTENDED_CANDLES = "candele_estese"
FIBONACCI_LEVELS = ("23.6%", "38.2%", "50%", "61.8%", "78.6%")
# Ten older candles far below the window: only the last N candles may set the range of the retracements.
OLDER = 10
OLDER_CLOSE = Decimal(30000)
# Half the spread between the high and the low of a candle of the known market.
HALF_SPREAD = Decimal(100)


@pytest.fixture
def flow_cycles() -> FlowCycles:
    return FlowCycles()


def the_flow(flow_cycles: FlowCycles) -> str:
    [flow] = flow_cycles.users
    return flow


def the_asset(flow_cycles: FlowCycles) -> str:
    [asset] = flow_cycles.flow(the_flow(flow_cycles)).configuration.assets
    return asset


def indicators_of(flow_cycles: FlowCycles, asset: str) -> dict[str, str]:
    [values] = flow_cycles.sources_in_context(INDICATORS, asset)
    return values


def number(text: str) -> Decimal:
    return Decimal(text.replace(",", "."))


def listed(text: str) -> list[Decimal]:
    """The numbers of an Italian list: "a, b e c"."""
    return [number(piece) for piece in text.replace(" e ", ", ").split(", ")]


def window_closes(count: int, low: Decimal, high: Decimal) -> list[Decimal]:
    """Closes that wander between the two extremes without touching them."""
    middle = (low + high) / 2
    amplitude = (high - low) / 4
    return [middle + amplitude * Decimal((index * 7) % 5 - 2) / 2 for index in range(count)]


def activate(flow_cycles: FlowCycles, flow: str, *indicators: str) -> None:
    flow_cycles.set_source_parameters(flow, INDICATORS, **dict.fromkeys(indicators, 1))


# Given


@given(quoted('che il flusso "{flow}" ha la fonte "{source}" con l\'asset "{asset}"'))
def flow_with_indicators(flow_cycles: FlowCycles, flow: str, source: str, asset: str) -> None:
    flow_cycles.add_flow(USER, flow, assets=(asset,), sources=(source,))


@given(quoted("che nelle ultime {count} candele a 4 ore il minimo è {low} e il massimo è {high}"))
def known_range(flow_cycles: FlowCycles, count: str, low: str, high: str) -> None:
    closes = [OLDER_CLOSE] * OLDER + window_closes(int(count), number(low), number(high))
    ranges = [(close + HALF_SPREAD, close - HALF_SPREAD) for close in closes]
    # One candle of the window touches the low, a later one the high.
    ranges[OLDER + 20] = (ranges[OLDER + 20][0], number(low))
    ranges[OLDER + 70] = (number(high), ranges[OLDER + 70][1])
    asset = the_asset(flow_cycles)
    flow_cycles.market.closes[asset, LONG] = closes
    flow_cycles.market.ranges[asset, LONG] = ranges


@given(quoted('che per "{asset}" ci sono solo {count} candele a 4 ore'))
def short_history(flow_cycles: FlowCycles, asset: str, count: str) -> None:
    flow_cycles.market.closes[asset, LONG] = window_closes(int(count), Decimal(50000), Decimal(60000))


# When


@when(quoted('"{user}" attiva l\'indicatore "{indicator}" e parte il ciclo'))
def activates_one(flow_cycles: FlowCycles, user: str, indicator: str) -> None:
    flow = the_flow(flow_cycles)
    assert flow_cycles.users[flow] == user
    activate(flow_cycles, flow, indicator)
    flow_cycles.run(flow)


@when(quoted('"{user}" attiva gli indicatori "{first}" e "{second}" e parte il ciclo'))
def activates_two(flow_cycles: FlowCycles, user: str, first: str, second: str) -> None:
    flow = the_flow(flow_cycles)
    assert flow_cycles.users[flow] == user
    activate(flow_cycles, flow, first, second)
    flow_cycles.run(flow)


@when(quoted("parte il ciclo con N uguale a {count}"))
def cycle_with_candles(flow_cycles: FlowCycles, count: str) -> None:
    flow = the_flow(flow_cycles)
    # N counts only for the extended indicators: all three are on, so that something is computed on the history.
    flow_cycles.set_source_parameters(flow, INDICATORS, **{EXTENDED_CANDLES: int(count)})
    activate(flow_cycles, flow, "fibonacci", "gann", "ciclo")
    flow_cycles.run(flow)


# Then


@then(quoted('il contesto contiene per "{asset}" i livelli {levels}'))
def fibonacci_levels(flow_cycles: FlowCycles, asset: str, levels: str) -> None:
    values = indicators_of(flow_cycles, asset)
    assert [number(values[f"lungo.fibonacci.{level}"]) for level in FIBONACCI_LEVELS] == listed(levels)


@then(quoted("il contesto contiene gli angoli di Gann 1x1, 1x2 e 2x1 e il ciclo dominante con periodo e fase"))
def gann_and_cycle(flow_cycles: FlowCycles) -> None:
    values = indicators_of(flow_cycles, the_asset(flow_cycles))
    assert values["lungo.gann.perno"] in {"minimo", "massimo"}
    assert all(number(values[f"lungo.gann.{angle}"]) > 0 for angle in ("1x1", "1x2", "2x1"))
    assert 4 <= int(values["lungo.ciclo.periodo_candele"]) <= 50
    assert 0 <= number(values["lungo.ciclo.fase_gradi"]) < 360


@then(quoted('il contesto dichiara "{note}" e calcola sulle {count}'))
def declared_short_history(flow_cycles: FlowCycles, note: str, count: str) -> None:
    values = indicators_of(flow_cycles, the_asset(flow_cycles))
    closes = window_closes(int(count), Decimal(50000), Decimal(60000))
    assert values["lungo.nota_storico"] == note
    assert values["lungo.candele_estese"] == count
    assert number(values["lungo.fibonacci.minimo"]) == min(closes) - 1
    assert number(values["lungo.fibonacci.massimo"]) == max(closes) + 1
