"""R5.1.6: behind the parameter "tendenza lunga" of the indicators source, the changes of the price over 7, 14, 30 and
60 days, the channel of the closes of the 20 days before the last one and the last daily close with its instant enter
the context of the cycle, computed on the closed UTC daily candles of the same market; a horizon without enough
history is declared among the missing data of the source. On the cycle the worker composes, with the fake market of
the exchange (ADR tendenza-lunga-sulle-candele-giornaliere).
"""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pytest_bdd import given, scenarios, then, when

from tests.support.flow_cycles import FlowCycles
from tests.support.steps import quoted

scenarios(
    "E5-evoluzioni/F5.1-nuove-fonti/R5.1.6-tendenza-su-orizzonti-lunghi-negli-indicatori/worker/R5.1.6-tendenza-su-orizzonti-lunghi-negli-indicatori.feature"
)

USER = "anna"
FLOW = "tendenza"
ASSET = "BTC"
INDICATORS = "indicatori"
LONG_TREND = "tendenza_lunga"
DAY = "1d"
TREND = "tendenza."
# A close per day that never repeats: each horizon has its own change.
RISING = Decimal(100)


def rising_closes(count: int) -> list[Decimal]:
    return [RISING + index for index in range(count)]


def change(last: Decimal, before: Decimal) -> Decimal:
    return (last / before - 1) * 100


def number(text: str) -> Decimal:
    return Decimal(text.replace(",", "."))


def the_asset(flow_cycles: FlowCycles) -> str:
    [asset] = flow_cycles.flow(FLOW).configuration.assets
    return asset


def indicators_of(flow_cycles: FlowCycles, asset: str) -> dict[str, str]:
    [values] = flow_cycles.sources_in_context(INDICATORS, asset)
    return values


def daily_closes(flow_cycles: FlowCycles, asset: str) -> list[Decimal]:
    return list(flow_cycles.market.closes[asset, DAY])


@pytest.fixture
def flow_cycles() -> FlowCycles:
    return FlowCycles()


# Given


@given(quoted('un flusso con la fonte indicatori e il parametro "tendenza lunga" a {value}'))
def flow_with_long_trend(flow_cycles: FlowCycles, value: str) -> None:
    flow_cycles.add_flow(USER, FLOW, assets=(ASSET,), sources=(INDICATORS,))
    flow_cycles.set_source_parameters(FLOW, INDICATORS, **{LONG_TREND: int(value)})


@given(quoted('un flusso con la fonte indicatori senza il parametro "tendenza lunga"'))
def flow_without_long_trend(flow_cycles: FlowCycles) -> None:
    flow_cycles.add_flow(USER, FLOW, assets=(ASSET,), sources=(INDICATORS,))


@given(quoted("{count} candele giornaliere chiuse disponibili per {asset}"))
def daily_history(flow_cycles: FlowCycles, count: str, asset: str) -> None:
    flow_cycles.market.closes[asset, DAY] = rising_closes(int(count))


@given(quoted("che la chiusura giornaliera di {days} giorni fa è {before} e l'ultima è {last}"))
def known_closes(flow_cycles: FlowCycles, days: str, before: str, last: str) -> None:
    closes = [Decimal(52000)] * (int(days) + 1)
    closes[0], closes[-1] = number(before), number(last)
    flow_cycles.market.closes[the_asset(flow_cycles), DAY] = closes


@given(quoted("che la giornata UTC corrente non è ancora chiusa"))
def day_still_open(flow_cycles: FlowCycles) -> None:
    now = flow_cycles.clock.now()
    assert now != now.replace(hour=0, minute=0, second=0, microsecond=0)
    flow_cycles.market.closes[the_asset(flow_cycles), DAY] = rising_closes(61)


@given(quoted("un asset con solo {count} candele giornaliere chiuse"))
def short_daily_history(flow_cycles: FlowCycles, count: str) -> None:
    flow_cycles.market.closes[the_asset(flow_cycles), DAY] = rising_closes(int(count))


# When


@when("parte un ciclo")
def a_cycle_starts(flow_cycles: FlowCycles) -> None:
    flow_cycles.run(FLOW)


# Then


@then(quoted("il contesto dell'agente contiene per {asset} la variazione percentuale a 7, 14, 30 e 60 giorni"))
def changes_over_days(flow_cycles: FlowCycles, asset: str) -> None:
    values = indicators_of(flow_cycles, asset)
    closes = daily_closes(flow_cycles, asset)
    assert [round(number(values[f"{TREND}variazione_{days}g"]), 4) for days in (7, 14, 30, 60)] == [
        round(change(closes[-1], closes[-1 - days]), 4) for days in (7, 14, 30, 60)
    ]


@then(quoted("il massimo e il minimo delle chiusure dei 20 giorni precedenti l'ultima chiusura"))
def channel_of_twenty_days(flow_cycles: FlowCycles) -> None:
    asset = the_asset(flow_cycles)
    values = indicators_of(flow_cycles, asset)
    previous = daily_closes(flow_cycles, asset)[-21:-1]
    assert number(values[f"{TREND}massimo_20g"]) == max(previous)
    assert number(values[f"{TREND}minimo_20g"]) == min(previous)


@then(quoted("l'ultima chiusura giornaliera con il suo istante"))
def last_daily_close(flow_cycles: FlowCycles) -> None:
    asset = the_asset(flow_cycles)
    values = indicators_of(flow_cycles, asset)
    assert number(values[f"{TREND}ultima_chiusura"]) == daily_closes(flow_cycles, asset)[-1]
    assert datetime.fromisoformat(values[f"{TREND}ultima_chiusura_istante"]).tzinfo == UTC


@then(quoted("la variazione a {days} giorni è {expected}"))
def change_over(flow_cycles: FlowCycles, days: str, expected: str) -> None:
    values = indicators_of(flow_cycles, the_asset(flow_cycles))
    assert number(values[f"{TREND}variazione_{days}g"]) == number(expected)


@then(quoted("l'ultima chiusura giornaliera è quella della giornata precedente"))
def last_close_of_the_previous_day(flow_cycles: FlowCycles) -> None:
    asset = the_asset(flow_cycles)
    values = indicators_of(flow_cycles, asset)
    now = flow_cycles.clock.now()
    start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    assert datetime.fromisoformat(values[f"{TREND}ultima_chiusura_istante"]) == start_of_today
    assert number(values[f"{TREND}ultima_chiusura"]) == daily_closes(flow_cycles, asset)[-1]


@then(quoted("il contesto dell'agente non contiene i valori di tendenza lunga"))
def no_long_trend(flow_cycles: FlowCycles) -> None:
    values = indicators_of(flow_cycles, the_asset(flow_cycles))
    assert values
    assert not [key for key in values if key.startswith(TREND)]


@then(quoted("la fonte non legge candele giornaliere"))
def no_daily_candles_read(flow_cycles: FlowCycles) -> None:
    assert flow_cycles.market.requests
    assert not [request for request in flow_cycles.market.requests if request[1] == DAY]


@then(quoted("il contesto contiene le variazioni a 7 e 14 giorni"))
def short_horizons(flow_cycles: FlowCycles) -> None:
    asset = the_asset(flow_cycles)
    values = indicators_of(flow_cycles, asset)
    closes = daily_closes(flow_cycles, asset)
    assert [round(number(values[f"{TREND}variazione_{days}g"]), 4) for days in (7, 14)] == [
        round(change(closes[-1], closes[-1 - days]), 4) for days in (7, 14)
    ]


@then(quoted("le variazioni a 30 e 60 giorni compaiono tra i dati mancanti"))
def long_horizons_missing(flow_cycles: FlowCycles) -> None:
    values = indicators_of(flow_cycles, the_asset(flow_cycles))
    missing = values[f"{TREND}dati_mancanti"]
    assert "variazione_30g" in missing
    assert "variazione_60g" in missing
    assert f"{TREND}variazione_30g" not in values
    assert f"{TREND}variazione_60g" not in values
