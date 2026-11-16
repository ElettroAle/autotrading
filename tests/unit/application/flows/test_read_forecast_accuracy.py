"""The mean error of the forecasts of a flow over the period the user chooses (R3.6.1, ADR
errore-medio-della-previsione-nell-api).
"""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

from autotrading.application.flows.errors import FlowNotFoundError
from autotrading.application.flows.read_forecast_accuracy import (
    ReadForecastAccuracyCommand,
    ReadForecastAccuracyUseCase,
)
from autotrading.domain.flows.errors import InvalidStatisticsPeriodError
from autotrading.domain.flows.flow import Flow
from autotrading.domain.sources.price_forecast import ForecastHorizon, PriceForecast
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.flow_forecasts import InMemoryFlowForecastsAdapter
from tests.fakes.flow_repository import FlowStore, InMemoryFlowRepositoryAdapter
from tests.fakes.forecast_repository import InMemoryForecastRepositoryAdapter
from tests.support.flows import a_flow

NOW = datetime(2026, 11, 16, 12, tzinfo=UTC)
TENANT = TenantId.new()


class Platform:
    def __init__(self) -> None:
        self.flows = FlowStore()
        self.recorded = InMemoryForecastRepositoryAdapter()

    def flow(self, tenant_id: TenantId = TENANT) -> Flow:
        flow = a_flow(tenant_id)
        self.flows.flows.append(flow)
        return flow

    def forecast(self, flow: Flow, predicted: str, actual: str | None, expires_at: datetime) -> None:
        horizon = ForecastHorizon.HOUR_1
        self.recorded.add(
            PriceForecast(
                flow.id.value,
                "BTC",
                horizon,
                expires_at - horizon.length,
                Decimal(60000),
                Decimal(predicted),
                7,
                False,
                None if actual is None else Decimal(actual),
            )
        )

    def use_case(self) -> ReadForecastAccuracyUseCase:
        return ReadForecastAccuracyUseCase(
            InMemoryFlowRepositoryAdapter(self.flows, TENANT),
            InMemoryFlowForecastsAdapter(self.recorded),
            lambda: NOW,
        )


@pytest.fixture
def platform() -> Platform:
    return Platform()


def test_the_error_of_the_whole_life_measures_every_expired_forecast(platform: Platform) -> None:
    flow = platform.flow()
    platform.forecast(flow, "60500", "60000", NOW - timedelta(days=20))
    platform.forecast(flow, "61000", "61400", NOW - timedelta(hours=1))

    (accuracy,) = platform.use_case().execute(ReadForecastAccuracyCommand(flow.id.value))

    assert (accuracy.asset, accuracy.horizon_minutes) == ("BTC", 60)
    assert accuracy.mean_absolute_error == Decimal(450)
    assert accuracy.mean_percent_error == Decimal("0.74")
    assert accuracy.evaluated == 2


def test_a_forecast_whose_horizon_has_not_expired_is_left_out(platform: Platform) -> None:
    flow = platform.flow()
    platform.forecast(flow, "60500", "60000", NOW - timedelta(hours=1))
    platform.forecast(flow, "60000", None, NOW + timedelta(minutes=30))

    (accuracy,) = platform.use_case().execute(ReadForecastAccuracyCommand(flow.id.value))

    assert (accuracy.evaluated, accuracy.unevaluable) == (1, 0)


def test_the_last_days_count_the_forecasts_expired_in_them(platform: Platform) -> None:
    flow = platform.flow()
    platform.forecast(flow, "60900", "60000", NOW - timedelta(days=10))
    platform.forecast(flow, "60300", "60000", NOW - timedelta(days=2))

    (accuracy,) = platform.use_case().execute(ReadForecastAccuracyCommand(flow.id.value, "7d"))

    assert accuracy.mean_absolute_error == Decimal(300)


def test_a_range_counts_the_forecasts_expired_in_its_days(platform: Platform) -> None:
    flow = platform.flow()
    platform.forecast(flow, "60900", "60000", datetime(2026, 11, 10, 11, tzinfo=UTC))
    platform.forecast(flow, "60300", "60000", datetime(2026, 11, 15, 11, tzinfo=UTC))
    command = ReadForecastAccuracyCommand(flow.id.value, "range", date(2026, 11, 14), date(2026, 11, 16))

    (accuracy,) = platform.use_case().execute(command)

    assert accuracy.mean_absolute_error == Decimal(300)


def test_a_flow_without_forecasts_has_no_error(platform: Platform) -> None:
    flow = platform.flow()

    assert platform.use_case().execute(ReadForecastAccuracyCommand(flow.id.value)) == ()


def test_the_forecasts_of_another_flow_do_not_count(platform: Platform) -> None:
    flow, other = platform.flow(), platform.flow()
    platform.forecast(other, "60500", "60000", NOW - timedelta(hours=1))

    assert platform.use_case().execute(ReadForecastAccuracyCommand(flow.id.value)) == ()


def test_a_flow_of_another_tenant_is_not_found(platform: Platform) -> None:
    flow = platform.flow(TenantId.new())

    with pytest.raises(FlowNotFoundError):
        platform.use_case().execute(ReadForecastAccuracyCommand(flow.id.value))


def test_an_unknown_period_is_refused(platform: Platform) -> None:
    flow = platform.flow()

    with pytest.raises(InvalidStatisticsPeriodError):
        platform.use_case().execute(ReadForecastAccuracyCommand(flow.id.value, "1y"))
