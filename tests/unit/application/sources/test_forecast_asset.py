from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from autotrading.application.sources.errors import SourceUnavailableError
from autotrading.application.sources.forecast_asset import ForecastAssetCommand, ForecastAssetUseCase
from autotrading.domain.sources.price_forecast import ForecastHorizon
from tests.fakes.forecast_repository import InMemoryForecastRepositoryAdapter
from tests.fakes.price_forecaster import FakePriceForecasterAdapter
from tests.fakes.price_history import FakePriceHistoryAdapter

NOW = datetime(2026, 11, 12, 10, 0, tzinfo=UTC)
FLOW = uuid4()
SHORT = (ForecastHorizon(15), ForecastHorizon(60))


def test_the_asset_is_forecast_at_every_horizon_and_recorded() -> None:
    prices = FakePriceHistoryAdapter(prices={"BTC": Decimal(100)})
    forecaster = FakePriceForecasterAdapter()
    forecasts = InMemoryForecastRepositoryAdapter()

    made = ForecastAssetUseCase(prices, forecaster, forecasts).execute(
        ForecastAssetCommand(FLOW, "BTC", 7, NOW, SHORT, 365)
    )

    assert [
        (forecast.horizon, forecast.last_price, forecast.predicted_price, forecast.history_days) for forecast in made
    ] == [
        (ForecastHorizon(15), Decimal(100), Decimal("100.15"), 7),
        (ForecastHorizon(60), Decimal(100), Decimal("100.60"), 7),
    ]
    assert forecasts.forecasts == list(made)
    assert (prices.requests, prices.daily_requests) == ([("BTC", 7)], [])
    assert forecaster.requests == [("BTC", 7, (ForecastHorizon(15), ForecastHorizon(60)))]


def test_the_forecast_of_a_trial_outside_every_flow_is_made_and_never_recorded() -> None:
    forecasts = InMemoryForecastRepositoryAdapter()

    made = ForecastAssetUseCase(FakePriceHistoryAdapter(), FakePriceForecasterAdapter(), forecasts).execute(
        ForecastAssetCommand(None, "BTC", 7, NOW, SHORT, 365)
    )

    assert [(forecast.flow_id, forecast.horizon) for forecast in made] == [
        (None, ForecastHorizon(15)),
        (None, ForecastHorizon(60)),
    ]
    assert forecasts.forecasts == []


def test_a_shorter_history_is_declared_by_every_forecast() -> None:
    prices = FakePriceHistoryAdapter(available_days=3)

    made = ForecastAssetUseCase(prices, FakePriceForecasterAdapter(), InMemoryForecastRepositoryAdapter()).execute(
        ForecastAssetCommand(FLOW, "BTC", 30, NOW, SHORT, 365)
    )

    assert {(forecast.history_days, forecast.shortened) for forecast in made} == {(3, True)}


def test_an_exchange_without_answer_records_nothing() -> None:
    forecasts = InMemoryForecastRepositoryAdapter()

    with pytest.raises(SourceUnavailableError):
        ForecastAssetUseCase(FakePriceHistoryAdapter(missing={"BTC"}), FakePriceForecasterAdapter(), forecasts).execute(
            ForecastAssetCommand(FLOW, "BTC", 7, NOW, SHORT, 365)
        )

    assert forecasts.forecasts == []


def test_a_forecaster_without_answer_records_nothing() -> None:
    forecasts = InMemoryForecastRepositoryAdapter()

    with pytest.raises(SourceUnavailableError):
        ForecastAssetUseCase(FakePriceHistoryAdapter(), FakePriceForecasterAdapter(missing={"BTC"}), forecasts).execute(
            ForecastAssetCommand(FLOW, "BTC", 7, NOW, SHORT, 365)
        )

    assert forecasts.forecasts == []


def test_the_long_horizon_chosen_is_forecast_on_the_daily_history_and_recorded() -> None:
    prices = FakePriceHistoryAdapter(prices={"BTC": Decimal(100)})
    forecaster = FakePriceForecasterAdapter()
    forecasts = InMemoryForecastRepositoryAdapter()

    made = ForecastAssetUseCase(prices, forecaster, forecasts).execute(
        ForecastAssetCommand(FLOW, "BTC", 7, NOW, (*SHORT, ForecastHorizon(1440)), 365)
    )

    assert [(forecast.horizon, forecast.predicted_price, forecast.history_days) for forecast in made] == [
        (ForecastHorizon(15), Decimal("100.15"), 7),
        (ForecastHorizon(60), Decimal("100.60"), 7),
        (ForecastHorizon(1440), Decimal("114.40"), 365),
    ]
    assert forecasts.forecasts == list(made)
    assert (prices.requests, prices.daily_requests) == ([("BTC", 7)], [("BTC", 365)])
    assert forecaster.requests == [
        ("BTC", 7, (ForecastHorizon(15), ForecastHorizon(60))),
        ("BTC", 365, (ForecastHorizon(1440),)),
    ]


def test_a_shorter_daily_history_is_declared_only_by_the_long_forecast() -> None:
    prices = FakePriceHistoryAdapter(daily_available_days=200)

    made = ForecastAssetUseCase(prices, FakePriceForecasterAdapter(), InMemoryForecastRepositoryAdapter()).execute(
        ForecastAssetCommand(FLOW, "BTC", 7, NOW, (*SHORT, ForecastHorizon(10080)), 365)
    )

    assert [(forecast.horizon, forecast.history_days, forecast.shortened) for forecast in made] == [
        (ForecastHorizon(15), 7, False),
        (ForecastHorizon(60), 7, False),
        (ForecastHorizon(10080), 200, True),
    ]


def test_a_daily_history_without_answer_records_not_even_the_short_forecasts() -> None:
    forecasts = InMemoryForecastRepositoryAdapter()

    with pytest.raises(SourceUnavailableError):
        ForecastAssetUseCase(
            FakePriceHistoryAdapter(daily_missing={"BTC"}), FakePriceForecasterAdapter(), forecasts
        ).execute(ForecastAssetCommand(FLOW, "BTC", 7, NOW, (*SHORT, ForecastHorizon(1440)), 365))

    assert forecasts.forecasts == []


def test_only_the_history_of_the_horizons_chosen_is_read() -> None:
    prices = FakePriceHistoryAdapter()
    forecaster = FakePriceForecasterAdapter()

    made = ForecastAssetUseCase(prices, forecaster, InMemoryForecastRepositoryAdapter()).execute(
        ForecastAssetCommand(FLOW, "BTC", 7, NOW, (ForecastHorizon(1440), ForecastHorizon(2160)), 365)
    )

    assert [forecast.horizon for forecast in made] == [ForecastHorizon(1440), ForecastHorizon(2160)]
    assert (prices.requests, prices.daily_requests) == ([], [("BTC", 365)])
    assert forecaster.requests == [("BTC", 365, (ForecastHorizon(1440), ForecastHorizon(2160)))]


def test_a_free_short_horizon_is_forecast_on_the_finest_history() -> None:
    prices = FakePriceHistoryAdapter()

    made = ForecastAssetUseCase(prices, FakePriceForecasterAdapter(), InMemoryForecastRepositoryAdapter()).execute(
        ForecastAssetCommand(FLOW, "BTC", 7, NOW, (ForecastHorizon(240),), 365)
    )

    assert [(forecast.horizon, forecast.history_days) for forecast in made] == [(ForecastHorizon(240), 7)]
    assert (prices.requests, prices.daily_requests) == ([("BTC", 7)], [])


def test_no_horizon_reads_nothing_and_forecasts_nothing() -> None:
    prices = FakePriceHistoryAdapter()

    made = ForecastAssetUseCase(prices, FakePriceForecasterAdapter(), InMemoryForecastRepositoryAdapter()).execute(
        ForecastAssetCommand(FLOW, "BTC", 7, NOW, (), 365)
    )

    assert made == ()
    assert (prices.requests, prices.daily_requests) == ([], [])
