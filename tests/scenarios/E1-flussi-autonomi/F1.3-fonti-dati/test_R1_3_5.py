from dataclasses import dataclass, field
from datetime import UTC, datetime, time
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from pytest_bdd import given, scenarios, then, when

from autotrading.application.sources.record_actual_prices import RecordActualPricesCommand, RecordActualPricesUseCase
from autotrading.domain.sources.price_forecast import ForecastHorizon, PriceForecast
from tests.fakes.forecast_repository import InMemoryForecastRepositoryAdapter
from tests.fakes.price_history import FakePriceHistoryAdapter
from tests.support.steps import quoted

scenarios("E1-flussi-autonomi/F1.3-fonti-dati/R1.3.5-forecast.feature")

DAY = datetime(2026, 11, 12, tzinfo=UTC).date()


@dataclass
class Forecasting:
    """The flows of the user, the prices of the exchange and the recorded forecasts."""

    flows: dict[str, UUID] = field(default_factory=dict)
    prices: FakePriceHistoryAdapter = field(default_factory=FakePriceHistoryAdapter)
    forecasts: InMemoryForecastRepositoryAdapter = field(default_factory=InMemoryForecastRepositoryAdapter)


def at(clock: str) -> datetime:
    return datetime.combine(DAY, time.fromisoformat(clock), UTC)


@pytest.fixture
def forecasting() -> Forecasting:
    return Forecasting()


@given(quoted('che "{user}" ha il flusso "{flow}" con asset "{asset}" e la fonte "{source}" attiva'))
def flow_with_forecast(forecasting: Forecasting, flow: str) -> None:
    forecasting.flows[flow] = uuid4()


@given(quoted('che alle {clock} il flusso "{flow}" ha registrato per "{asset}" una previsione a 15 minuti di {price}'))
def recorded_forecast(forecasting: Forecasting, clock: str, flow: str, asset: str, price: str) -> None:
    forecasting.forecasts.add(
        PriceForecast(
            forecasting.flows[flow],
            asset,
            ForecastHorizon.MINUTES_15,
            at(clock),
            Decimal(100),
            Decimal(price),
            7,
            False,
        )
    )


@when(quoted('arrivano le {clock} e il prezzo di "{asset}" è {price}'))
def horizon_expires(forecasting: Forecasting, clock: str, asset: str, price: str) -> None:
    forecasting.prices.prices[asset] = Decimal(price)
    RecordActualPricesUseCase(forecasting.prices, forecasting.forecasts).execute(RecordActualPricesCommand(at(clock)))


@then(quoted('la previsione delle {clock} per "{asset}" a 15 minuti ha registrato il prezzo effettivo {price}'))
def actual_price_recorded(forecasting: Forecasting, clock: str, asset: str, price: str) -> None:
    recorded = [
        forecast.actual_price
        for forecast in forecasting.forecasts.forecasts
        if (forecast.made_at, forecast.asset, forecast.horizon) == (at(clock), asset, ForecastHorizon.MINUTES_15)
    ]
    assert recorded == [Decimal(price)]
