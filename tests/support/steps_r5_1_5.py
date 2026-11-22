"""R5.1.5: the forecast source also forecasts 1 day and 1 week ahead, on the daily candles of the exchange; every long
forecast is recorded and gets its actual price when it expires, as the short ones; a horizon outside the admitted ones
is refused naming them. On the cycle the worker composes and on the modification of the flow (ADR
orizzonti-lunghi-del-forecast); the horizons are a list of the flow, the long one added to the default ones (ADR
parametri-delle-fonti-come-liste-libere).
"""

from datetime import timedelta
from decimal import Decimal

import pytest
from pytest_bdd import given, then, when

from autotrading.application.flows.create_flow import SourceRequest
from autotrading.application.flows.ports import AdapterRequest
from autotrading.application.flows.read_forecast_accuracy import ReadForecastAccuracyCommand
from autotrading.domain.flows.forecast_accuracy import ForecastAccuracy
from autotrading.domain.sources.forecast import HORIZONS
from autotrading.domain.sources.price_forecast import ForecastHorizon, PriceForecast
from tests.support.flow_cycles import FlowCycles, at
from tests.support.lifecycle_steps import Lifecycle, modify
from tests.support.steps import quoted

USER = "anna"
FORECAST = "forecast"
MINUTES_PER_DAY = 24 * 60
# What a user means by the words of a horizon, in minutes: the months as thirty days.
UNIT_MINUTES = {
    "giorno": MINUTES_PER_DAY,
    "giorni": MINUTES_PER_DAY,
    "settimana": 7 * MINUTES_PER_DAY,
    "settimane": 7 * MINUTES_PER_DAY,
    "mese": 30 * MINUTES_PER_DAY,
    "mesi": 30 * MINUTES_PER_DAY,
}
ACTUAL_PRICE = Decimal(64250)


@pytest.fixture
def flow_cycles() -> FlowCycles:
    return FlowCycles()


@pytest.fixture
def lifecycle() -> Lifecycle:
    return Lifecycle()


@pytest.fixture
def accuracies() -> list[ForecastAccuracy]:
    """The errors of the forecasts the user read, for the asset and horizon asked."""
    return []


def the_flow(flow_cycles: FlowCycles) -> str:
    [flow] = flow_cycles.users
    return flow


def the_asset(flow_cycles: FlowCycles) -> str:
    [asset] = flow_cycles.flow(the_flow(flow_cycles)).configuration.assets
    return asset


def minutes_of(horizon: str) -> int:
    count, unit = horizon.split(" ")
    return int(count) * UNIT_MINUTES[unit]


def set_horizon(flow_cycles: FlowCycles, lifecycle: Lifecycle, user: str, horizon: str) -> None:
    """The modification of the flow as the API makes it: the forecast with its adapter and the long horizon chosen."""
    flow = the_flow(flow_cycles)
    [adapter] = flow_cycles.platform.use_cases_of(user).list_sources.execute().find(FORECAST).adapters
    horizons = (*HORIZONS.default, minutes_of(horizon))
    request = SourceRequest(FORECAST, (AdapterRequest(adapter.name, None, {HORIZONS.key: horizons}),))
    modify(flow_cycles.platform, lifecycle, user, flow, sources=(request,))


# Given


@given(quoted('che il flusso "{flow}" ha la fonte "{source}" sull\'asset "{asset}"'))
def flow_with_forecast(flow_cycles: FlowCycles, flow: str, source: str, asset: str) -> None:
    flow_cycles.add_flow(USER, flow, assets=(asset,), sources=(source,))


@given(quoted('che per "{asset}" sono disponibili solo {days} giorni di storico giornaliero'))
def short_daily_history(flow_cycles: FlowCycles, asset: str, days: str) -> None:
    assert asset == the_asset(flow_cycles)
    flow_cycles.prices.daily_available_days = int(days)


@given("che ieri alle 10:00 è stata registrata una previsione a 1 giorno")
def recorded_yesterday(flow_cycles: FlowCycles) -> None:
    flow = flow_cycles.flow(the_flow(flow_cycles))
    yesterday = at("10:00") - timedelta(days=1)
    forecast = PriceForecast(
        flow.id.value,
        the_asset(flow_cycles),
        ForecastHorizon(1440),
        yesterday,
        Decimal(64000),
        Decimal(64500),
        365,
        False,
    )
    flow_cycles.forecasts_of(flow.tenant_id).add(forecast)


# When


@when(quoted('"{user}" imposta l\'orizzonte "{horizon}" e parte il ciclo'))
def horizon_and_cycle(flow_cycles: FlowCycles, lifecycle: Lifecycle, user: str, horizon: str) -> None:
    set_horizon(flow_cycles, lifecycle, user, horizon)
    assert lifecycle.error is None
    flow_cycles.run(the_flow(flow_cycles))


@when(quoted('"{user}" imposta l\'orizzonte "{horizon}"'))
def horizon_only(flow_cycles: FlowCycles, lifecycle: Lifecycle, user: str, horizon: str) -> None:
    set_horizon(flow_cycles, lifecycle, user, horizon)


@given("che sono passate le 10:00 di oggi")
@when("passano le 10:00 di oggi")
def ten_today(flow_cycles: FlowCycles) -> None:
    flow_cycles.prices.prices[the_asset(flow_cycles)] = ACTUAL_PRICE
    flow_cycles.clock.current = at("10:00")
    flow_cycles.plan_round()


@when(quoted('"{user}" consulta l\'errore della previsione di "{asset}" a {horizon}'))
def reads_accuracy(
    flow_cycles: FlowCycles, accuracies: list[ForecastAccuracy], user: str, asset: str, horizon: str
) -> None:
    flow = flow_cycles.flow(the_flow(flow_cycles))
    # The API reads the forecasts the worker recorded, in the one database of the installation, at the same instant.
    platform = flow_cycles.platform
    platform.forecasts[flow.tenant_id] = flow_cycles.forecasts_of(flow.tenant_id)
    platform.now = flow_cycles.clock.now()
    command = ReadForecastAccuracyCommand(flow.id.value)
    seen = platform.use_cases_of(user).read_forecast_accuracy.execute(command)
    accuracies[:] = [
        accuracy for accuracy in seen if (accuracy.asset, accuracy.horizon_minutes) == (asset, minutes_of(horizon))
    ]


# Then


@then(quoted('il contesto contiene la previsione di "{asset}" a {horizon} con il suo istante di riferimento'))
def long_forecast_in_context(flow_cycles: FlowCycles, asset: str, horizon: str) -> None:
    chosen = ForecastHorizon(minutes_of(horizon))
    [values] = flow_cycles.sources_in_context(FORECAST, asset)
    flow = flow_cycles.flow(the_flow(flow_cycles))
    [sample] = [kept for kept in flow_cycles.samples_of(flow.tenant_id).samples if kept.source == FORECAST]
    [long] = [kept for kept in flow_cycles.forecasts_of(flow.tenant_id).forecasts if kept.horizon == chosen]
    assert Decimal(values[f"prezzo_previsto_{chosen.label}"]) == long.predicted_price
    assert sample.reference_at == long.made_at == flow_cycles.clock.now()


@then(quoted('il contesto dichiara per "{asset}" lo storico giornaliero ridotto a {days} giorni'))
def shortened_daily_history(flow_cycles: FlowCycles, asset: str, days: str) -> None:
    [values] = flow_cycles.sources_in_context(FORECAST, asset)
    assert values["profondita_storico_lunga_giorni"] == days
    assert "storico_lungo_ridotto" in values


@then("la previsione riceve il prezzo effettivo delle 10:00 di oggi")
def actual_price_of_today(flow_cycles: FlowCycles) -> None:
    flow = flow_cycles.flow(the_flow(flow_cycles))
    yesterday = at("10:00") - timedelta(days=1)
    [daily] = [
        kept
        for kept in flow_cycles.forecasts_of(flow.tenant_id).forecasts
        if (kept.horizon, kept.made_at) == (ForecastHorizon(1440), yesterday)
    ]
    assert daily.actual_price == ACTUAL_PRICE


@then(quoted('la configurazione è rifiutata con motivo "{reason}"'))
def refused_with_reason(lifecycle: Lifecycle, reason: str) -> None:
    assert str(lifecycle.error) == reason


@then(quoted("l'errore medio assoluto a {horizon} è {error} su {count} previsione valutata"))
def long_accuracy(accuracies: list[ForecastAccuracy], horizon: str, error: str, count: str) -> None:
    [accuracy] = accuracies
    assert accuracy.horizon_minutes == minutes_of(horizon)
    assert (accuracy.mean_absolute_error, accuracy.evaluated) == (Decimal(error), int(count))
