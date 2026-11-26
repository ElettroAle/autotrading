"""R5.5.4: the Hyperliquid adapter of the indicators gives, when the flow asks, the distance of the price from the low
and the high of the last hours, the change over hours and the series of the closes; run as the API and the worker
compose them, with the fake market of the exchange (ADR dati-di-regime-nella-fonte-indicatori).

The hourly candles of the fake market close on the hour: at the hour of the cycles the last one closed just now, so the
close of N hours ago is the one N candles before it.
"""

import json
import re
from dataclasses import dataclass, replace
from decimal import Decimal

import pytest
from pytest_bdd import given, parsers, then, when

from autotrading.application.flows.create_flow import SourceRequest
from autotrading.application.flows.get_flow import GetFlowCommand
from autotrading.application.flows.modify_flow import ModifyFlowCommand
from autotrading.application.flows.ports import AdapterRequest
from autotrading.domain.errors import AutotradingError
from autotrading.domain.flows.cycle_record import CycleOutcome
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_configuration import FlowConfiguration
from autotrading.domain.flows.selections import AdapterSelection
from autotrading.domain.sources.source_parameter import SourceParameterValue
from tests.fakes.market_data import DEFAULT_CLOSES, DEFAULT_SNAPSHOT
from tests.support.flow_cycles import FlowCycles
from tests.support.steps import quoted

INDICATORS = "indicatori"
HOURLY = "1h"
SHORT = "15m"
LONG = "4h"
EXTREMES = "estremi."
MISSING = "dati_mancanti"
REGIME_KEYS = ("estremi_ore", "variazione_ore", "serie_chiusure")
LIST = r"\[[^\]]*\]"
EXTREME_VALUES = ("minimo", "massimo", "dal_minimo", "dal_massimo")
HOURLY_CHANGE = re.compile(r"^tendenza\.variazione_\d+h$")
# Lows and highs of the candles before the window: beyond the ones of the scenario, so only the window makes them.
LOW_BEFORE, HIGH_BEFORE = Decimal("2.00"), Decimal("3.50")


@dataclass
class RegimeData:
    """The flow of the scenario with the indicators of its adapter, the cycles that run it, what the user changed and
    read."""

    flow_cycles: FlowCycles
    adapter: str = ""
    error: AutotradingError | None = None
    version_before: int = 0
    read: Flow | None = None

    def adapter_of(self, flow: Flow) -> AdapterSelection:
        [source] = [source for source in flow.configuration.sources if source.name == INDICATORS]
        [adapter] = [adapter for adapter in source.adapters if adapter.name == self.adapter]
        return adapter

    def declared(self, user: str, key: str, saved: dict[str, SourceParameterValue]) -> SourceParameterValue:
        """The value in force of a parameter of the adapter: the saved one, the default the adapter declares if none."""
        catalog = self.flow_cycles.platform.use_cases_of(user).list_sources.execute()
        [parameter] = [
            parameter for parameter in catalog.find(INDICATORS).parameters_of(self.adapter) if parameter.key == key
        ]
        return parameter.value_in(saved)

    def modify(self, user: str, flow: str, key: str, value: SourceParameterValue) -> None:
        """The modification as the API makes it: the indicators of the flow with the adapter and the value asked."""
        self.version_before = self.flow_cycles.flow(flow).configuration.version
        request = SourceRequest(INDICATORS, (AdapterRequest(self.adapter, None, {key: value}),))
        command = ModifyFlowCommand(self.flow_cycles.flow(flow).id, sources=(request,))
        try:
            self.flow_cycles.platform.use_cases_of(user).modify_flow.execute(command)
        except AutotradingError as error:
            self.error = error

    def set_parameters(self, flow: str, **parameters: int | tuple[int, ...]) -> None:
        self.flow_cycles.set_source_parameters(flow, INDICATORS, **parameters)

    def indicators_of(self, asset: str) -> dict[str, str]:
        [values] = self.flow_cycles.sources_in_context(INDICATORS, asset)
        return values


@pytest.fixture
def regime() -> RegimeData:
    return RegimeData(FlowCycles())


def numbers(text: str) -> tuple[int, ...]:
    """The numbers of a list as the scenario writes it: "[24, 72]", "[]"."""
    inside = text.strip().removeprefix("[").removesuffix("]")
    return tuple(int(piece) for piece in inside.split(",") if piece.strip())


def number(text: str) -> Decimal:
    return Decimal(text.replace(",", "."))


def without_regime(configuration: FlowConfiguration) -> FlowConfiguration:
    """The configuration as it was saved before the regime data: no key of theirs among the parameters."""
    sources = tuple(
        replace(
            source,
            adapters=tuple(
                replace(
                    adapter,
                    parameters={key: value for key, value in adapter.parameters.items() if key not in REGIME_KEYS},
                )
                for adapter in source.adapters
            ),
        )
        for source in configuration.sources
    )
    return replace(configuration, sources=sources)


# Given


@given(
    quoted(
        'che "{user}" ha il flusso "{flow}" attivo con asset "{asset}" e la fonte indicatori con l\'adapter "{adapter}"'
    )
)
def flow_with_indicators(regime: RegimeData, user: str, flow: str, asset: str, adapter: str) -> None:
    regime.adapter = adapter
    regime.flow_cycles.add_flow(user, flow, assets=(asset,), sources=(INDICATORS,))
    assert regime.adapter_of(regime.flow_cycles.flow(flow)).name == adapter


@given(quoted('che il prezzo di "{asset}" è {price}'))
def price_of(regime: RegimeData, asset: str, price: str) -> None:
    regime.flow_cycles.market.snapshots[asset] = replace(DEFAULT_SNAPSHOT, price=number(price))


@given(quoted('che il flusso "{flow}" esisteva prima dei dati di regime'))
def flow_from_before(regime: RegimeData, flow: str) -> None:
    regime.flow_cycles.reconfigure(flow, without_regime)
    saved = regime.adapter_of(regime.flow_cycles.flow(flow)).parameters
    assert not set(REGIME_KEYS) & set(saved)
    regime.version_before = regime.flow_cycles.flow(flow).configuration.version


@given(parsers.re(rf"^che l'adapter ha estremi_ore (?P<hours>{LIST})$"))
def extremes_hours(regime: RegimeData, hours: str) -> None:
    regime.set_parameters("alfa", estremi_ore=numbers(hours))


@given(parsers.re(rf"^che l'adapter ha variazione_ore (?P<hours>{LIST})$"))
def change_hours(regime: RegimeData, hours: str) -> None:
    regime.set_parameters("alfa", variazione_ore=numbers(hours))


@given(quoted("che l'adapter ha serie_chiusure {flag} e lunghezza della serie {length}"))
def close_series(regime: RegimeData, flag: str, length: str) -> None:
    regime.set_parameters("alfa", serie_chiusure=int(flag), lunghezza_serie=int(length))


@given("che l'adapter ha estremi_ore vuoto, variazione_ore vuoto e serie_chiusure 0")
def regime_off(regime: RegimeData) -> None:
    regime.set_parameters("alfa", estremi_ore=(), variazione_ore=(), serie_chiusure=0)


@given(quoted('che le ultime {count} candele orarie chiuse di "{asset}" hanno minimo {low} e massimo {high}'))
def hourly_extremes(regime: RegimeData, count: str, asset: str, low: str, high: str) -> None:
    window = int(count)
    middle = (number(low) + number(high)) / 2
    inside = [(middle, middle)] * window
    inside[0], inside[-1] = (number(high), middle), (middle, number(low))
    before = [(HIGH_BEFORE, LOW_BEFORE)] * 10
    regime.flow_cycles.market.closes[asset, HOURLY] = [middle] * (len(before) + window)
    regime.flow_cycles.market.ranges[asset, HOURLY] = [*before, *inside]


@given(quoted('che la chiusura di "{asset}" di {hours} ore fa è {close}'))
def close_hours_ago(regime: RegimeData, asset: str, hours: str, close: str) -> None:
    closes = [Decimal("2.60")] * (int(hours) + 10)
    closes[-1 - int(hours)] = number(close)
    regime.flow_cycles.market.closes[asset, HOURLY] = closes


@given(quoted('che l\'exchange ha per "{asset}" solo {hours} ore di storico'))
def short_hourly_history(regime: RegimeData, asset: str, hours: str) -> None:
    regime.flow_cycles.market.closes[asset, HOURLY] = [Decimal("2.60")] * int(hours)


# When


@when(quoted('"{user}" legge la configurazione di "{flow}"'))
def reads_configuration(regime: RegimeData, user: str, flow: str) -> None:
    command = GetFlowCommand(regime.flow_cycles.flow(flow).id)
    regime.read = regime.flow_cycles.platform.use_cases_of(user).get_flow.execute(command)


@when(
    parsers.re(
        r'^"(?P<user>[^"]+)" imposta (?P<key>\w+) dell\'adapter "[^"]+" degli indicatori di "(?P<flow>[^"]+)" a '
        rf"(?P<value>{LIST}|\d+)$"
    )
)
def sets_parameter(regime: RegimeData, user: str, key: str, flow: str, value: str) -> None:
    regime.modify(user, flow, key, numbers(value) if value.startswith("[") else int(value))


@when(quoted('parte il ciclo di "{flow}"'))
def cycle_starts(regime: RegimeData, flow: str) -> None:
    regime.flow_cycles.run(flow)


# Then


@then(
    quoted(
        'l\'adapter "{adapter}" degli indicatori di "{flow}" ha estremi_ore vuoto, variazione_ore vuoto e '
        "serie_chiusure 0"
    )
)
def regime_empty(regime: RegimeData, adapter: str, flow: str) -> None:
    assert regime.read is not None
    assert regime.adapter == adapter
    saved = dict(regime.adapter_of(regime.read).parameters)
    user = regime.flow_cycles.users[flow]
    assert regime.declared(user, "estremi_ore", saved) == ()
    assert regime.declared(user, "variazione_ore", saved) == ()
    assert regime.declared(user, "serie_chiusure", saved) == 0


@then(quoted('la configurazione di "{flow}" resta alla stessa versione'))
def same_version(regime: RegimeData, flow: str) -> None:
    assert regime.flow_cycles.flow(flow).configuration.version == regime.version_before


@then(quoted('la modifica viene rifiutata con "{reason}"'))
def refused(regime: RegimeData, reason: str) -> None:
    assert regime.error is not None
    assert str(regime.error) == reason
    assert regime.flow_cycles.flow("alfa").configuration.version == regime.version_before


@then(parsers.re(rf'^"(?P<flow>[^"]+)" ha una nuova versione della configurazione con estremi_ore (?P<hours>{LIST})$'))
def new_version(regime: RegimeData, flow: str, hours: str) -> None:
    assert regime.error is None
    recorded = regime.flow_cycles.flow(flow)
    assert recorded.configuration.version == regime.version_before + 1
    assert regime.adapter_of(recorded).parameters["estremi_ore"] == numbers(hours)


@then(quoted('l\'agente riceve per "{asset}" estremi.minimo_{hours}h {low} ed estremi.massimo_{hours_again}h {high}'))
def extremes_received(regime: RegimeData, asset: str, *, hours: str, low: str, hours_again: str, high: str) -> None:
    values = regime.indicators_of(asset)
    assert number(values[f"{EXTREMES}minimo_{hours}h"]) == number(low)
    assert number(values[f"{EXTREMES}massimo_{hours_again}h"]) == number(high)


@then(
    quoted(
        'l\'agente riceve per "{asset}" estremi.dal_minimo_{hours}h {from_low} ed estremi.dal_massimo_{hours_again}h '
        "{from_high}"
    )
)
def distances_received(
    regime: RegimeData, asset: str, *, hours: str, from_low: str, hours_again: str, from_high: str
) -> None:
    values = regime.indicators_of(asset)
    assert number(values[f"{EXTREMES}dal_minimo_{hours}h"]) == number(from_low)
    assert number(values[f"{EXTREMES}dal_massimo_{hours_again}h"]) == number(from_high)


@then(
    quoted(
        'l\'agente riceve per "{asset}" i quattro valori di estremi a {first}h e i quattro valori di estremi a '
        "{second}h"
    )
)
def two_windows(regime: RegimeData, asset: str, first: str, second: str) -> None:
    received = {key for key in regime.indicators_of(asset) if key.startswith(EXTREMES)}
    expected = {f"{EXTREMES}{value}_{hours}h" for hours in (first, second) for value in EXTREME_VALUES}
    assert received == expected


@then(quoted('l\'agente riceve per "{asset}" tendenza.variazione_{hours}h {change}'))
def change_received(regime: RegimeData, asset: str, hours: str, change: str) -> None:
    assert number(regime.indicators_of(asset)[f"tendenza.variazione_{hours}h"]) == number(change)


@then(
    quoted(
        'l\'agente riceve per "{asset}" breve.chiusura.serie e lungo.chiusura.serie con {count} prezzi ciascuna, dal '
        "più vecchio al più recente"
    )
)
def close_series_received(regime: RegimeData, asset: str, count: str) -> None:
    values = regime.indicators_of(asset)
    market = regime.flow_cycles.market
    for prefix, timeframe in (("breve", SHORT), ("lungo", LONG)):
        series = json.loads(values[f"{prefix}.chiusura.serie"], parse_float=Decimal, parse_int=Decimal)
        closes = list(market.closes.get((asset, timeframe), DEFAULT_CLOSES))
        assert series == closes[-int(count) :]


@then(
    quoted(
        'l\'agente non riceve per "{asset}" nessun valore di estremi, nessuna variazione a ore e nessuna serie di '
        "chiusure"
    )
)
def nothing_of_the_regime(regime: RegimeData, asset: str) -> None:
    values = regime.indicators_of(asset)
    assert values
    assert not [key for key in values if key.startswith(EXTREMES)]
    assert not [key for key in values if HOURLY_CHANGE.match(key)]
    assert not [key for key in values if key.endswith(".chiusura.serie")]


@then(quoted('i dati mancanti del ciclo riportano i valori di estremi a {hours}h di "{asset}"'))
def extremes_missing(regime: RegimeData, hours: str, asset: str) -> None:
    values = regime.indicators_of(asset)
    for value in EXTREME_VALUES:
        assert f"{EXTREMES}{value}_{hours}h" in values[MISSING]
        assert f"{EXTREMES}{value}_{hours}h" not in values


@then(quoted('il ciclo di "{flow}" si conclude'))
def cycle_completed(regime: RegimeData, flow: str) -> None:
    assert regime.flow_cycles.last_record(flow).outcome is CycleOutcome.COMPLETED
