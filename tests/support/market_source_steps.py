"""The steps of the scenarios on the market data sources: technical indicators and pivot points (R1.3.3, R1.3.4).

A scenario module imports them next to the cycle steps; pytest-bdd keeps each step as a fixture of that module.
"""

import json
from dataclasses import replace
from decimal import Decimal

from pytest_bdd import given, parsers, then

from autotrading.application.sources.read_indicators import text_of
from autotrading.domain.flows.cycle_interval import CycleInterval
from autotrading.domain.flows.flow_configuration import FlowConfiguration
from autotrading.domain.sources.indicator_series import WARM_UP
from autotrading.domain.sources.market_snapshot import MarketSnapshot
from autotrading.domain.sources.pivot_levels import DailyRange
from autotrading.domain.sources.technical_indicators import exponential_moving_average
from tests.fakes.market_data import DEFAULT_SNAPSHOT
from tests.support.flow_cycles import FlowCycles
from tests.support.steps import quoted

TIMEFRAMES = {"15 minuti": ("breve", "15m"), "4 ore": ("lungo", "4h")}
# A series whose EMA20 differs from any average of the default market.
KNOWN_CLOSES = tuple(Decimal(200) + Decimal(index * index % 37) / 10 for index in range(200))
# Every indicator of the two timeframes is given as a series: 8 on the short one, 10 on the long one.
SERIES_COUNT = 18


def number(text: str) -> Decimal:
    return Decimal(text.replace(",", "."))


def indicators_of(flow_cycles: FlowCycles, asset: str) -> dict[str, str]:
    [values] = flow_cycles.sources_in_context("indicatori", asset)
    return values


def pivots_of(flow_cycles: FlowCycles, asset: str) -> dict[str, str]:
    [values] = flow_cycles.sources_in_context("pivot", asset)
    return values


def series_of(values: dict[str, str], key: str) -> list[Decimal]:
    return [Decimal(str(point)) for point in json.loads(values[f"{key}.serie"])]


# Given


@given(
    quoted(
        'che "{user}" ha il flusso "{flow}" con asset "{assets}", intervallo di ciclo di {minutes} minuti e la fonte '
        '"{source}" attiva'
    )
)
def flow_with_interval(  # noqa: PLR0917 - one argument per value of the step
    flow_cycles: FlowCycles, user: str, flow: str, assets: str, minutes: str, source: str
) -> None:
    def every(configuration: FlowConfiguration) -> FlowConfiguration:
        return replace(configuration, cycle_interval=CycleInterval(int(minutes)))

    flow_cycles.add_flow(user, flow, assets=tuple(assets.split(", ")), sources=(source,))
    flow_cycles.reconfigure(flow, every)


@given(quoted('che l\'exchange del conto riporta per "{asset}" le chiusure a 15 minuti di una serie nota'))
def known_closes(flow_cycles: FlowCycles, asset: str) -> None:
    flow_cycles.market.closes[asset, "15m"] = KNOWN_CLOSES


@given(quoted('che il flusso "{flow}" ha la lunghezza della serie degli indicatori a {length}'))
def series_length(flow_cycles: FlowCycles, flow: str, length: str) -> None:
    flow_cycles.set_source_parameters(flow, "indicatori", lunghezza_serie=int(length))


@given(quoted('che la giornata UTC precedente di "{asset}" ha massimo {high}, minimo {low} e chiusura {close}'))
def previous_day(flow_cycles: FlowCycles, asset: str, high: str, low: str, close: str) -> None:
    flow_cycles.market.days[asset] = DailyRange(high=number(high), low=number(low), close=number(close))


@given(quoted('che il prezzo corrente di "{asset}" è {price}'))
def current_price(flow_cycles: FlowCycles, asset: str, price: str) -> None:
    flow_cycles.market.snapshots[asset] = replace(DEFAULT_SNAPSHOT, price=number(price))


# Then: the indicators


@then(
    quoted(
        'il contesto contiene per "{asset}" sul timeframe di {timeframe} i valori correnti e le serie di {length} '
        "valori di:"
    )
)
def indicators_on_timeframe(
    flow_cycles: FlowCycles, asset: str, timeframe: str, length: str, datatable: list[list[str]]
) -> None:
    values = indicators_of(flow_cycles, asset)
    prefix, label = TIMEFRAMES[timeframe]
    assert values[f"{prefix}.timeframe"] == label
    for [name] in datatable[1:]:
        key = f"{prefix}.{name.strip()}"
        series = series_of(values, key)
        assert len(series) == int(length)
        assert Decimal(values[key]) == series[-1]


@then(quoted('il contesto contiene per "{asset}" prezzo corrente, mid price, open interest e funding rate'))
def market_values(flow_cycles: FlowCycles, asset: str) -> None:
    values = indicators_of(flow_cycles, asset)
    expected: MarketSnapshot = DEFAULT_SNAPSHOT
    assert [values[key] for key in ("prezzo", "mid_price", "open_interest", "funding_rate")] == [
        text_of(expected.price),
        text_of(expected.mid),
        text_of(expected.open_interest),
        text_of(expected.funding_rate),
    ]


@then(
    quoted(
        'il valore corrente di EMA20 per "{asset}" sul timeframe di 15 minuti coincide con quello calcolato sulla '
        "serie nota"
    )
)
def ema_on_known_series(flow_cycles: FlowCycles, asset: str) -> None:
    asked = KNOWN_CLOSES[-(10 + WARM_UP) :]
    assert indicators_of(flow_cycles, asset)["breve.EMA20"] == text_of(exponential_moving_average(asked, 20)[-1])


@then(quoted('le serie degli indicatori per "{asset}" hanno {length} valori'))
def every_series_length(flow_cycles: FlowCycles, asset: str, length: str) -> None:
    values = indicators_of(flow_cycles, asset)
    series = [key.removesuffix(".serie") for key in values if key.endswith(".serie")]
    assert len(series) == SERIES_COUNT
    assert all(len(series_of(values, key)) == int(length) for key in series)


# Then: the pivots


@then(quoted('il contesto contiene per "{asset}" i livelli:'))
def pivot_levels(flow_cycles: FlowCycles, asset: str, datatable: list[list[str]]) -> None:
    values = pivots_of(flow_cycles, asset)
    rows = [(name.strip(), value.strip()) for name, value in datatable[1:]]
    assert {name: number(values[name]) for name, _ in rows} == {name: number(value) for name, value in rows}


@then(quoted('il contesto indica per "{asset}" il prezzo {side} il PP'))
def price_side(flow_cycles: FlowCycles, asset: str, side: str) -> None:
    assert pivots_of(flow_cycles, asset)["posizione_rispetto_al_pp"] == side


@then(
    parsers.re(
        r'^il contesto indica per "(?P<asset>[^"]+)" la resistenza più vicina (?P<level>\w+) '
        r"a distanza (?P<percent>[\d,]+)%$"
    )
)
def nearest_resistance(flow_cycles: FlowCycles, asset: str, level: str, percent: str) -> None:
    values = pivots_of(flow_cycles, asset)
    assert (values["resistenza_vicina"], number(values["distanza_resistenza_percentuale"])) == (level, number(percent))


@then(
    parsers.re(
        r'^il contesto indica per "(?P<asset>[^"]+)" il supporto più vicino (?P<level>\w+) '
        r"a distanza (?P<percent>[\d,]+)%$"
    )
)
def nearest_support(flow_cycles: FlowCycles, asset: str, level: str, percent: str) -> None:
    values = pivots_of(flow_cycles, asset)
    assert (values["supporto_vicino"], number(values["distanza_supporto_percentuale"])) == (level, number(percent))


@then(quoted('il contesto indica per "{asset}" nessuna resistenza sopra il prezzo'))
def no_resistance(flow_cycles: FlowCycles, asset: str) -> None:
    values = pivots_of(flow_cycles, asset)
    assert values["resistenza_vicina"] == "nessuna resistenza sopra il prezzo"
    assert "distanza_resistenza_percentuale" not in values
