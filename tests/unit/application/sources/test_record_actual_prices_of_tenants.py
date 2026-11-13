"""The actual prices beside the expired forecasts of every tenant the worker plans for (R1.3.5)."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from autotrading.application.sources.record_actual_prices import RecordActualPricesCommand
from autotrading.application.sources.record_actual_prices_of_tenants import RecordActualPricesOfTenantsUseCase
from autotrading.domain.sources.price_forecast import ForecastHorizon, PriceForecast
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.forecast_repository import InMemoryForecastRepositoryAdapter
from tests.fakes.price_history import FakePriceHistoryAdapter

TEN = datetime(2026, 11, 12, 10, 0, tzinfo=UTC)


def expired_forecasts() -> InMemoryForecastRepositoryAdapter:
    repository = InMemoryForecastRepositoryAdapter()
    repository.add(PriceForecast(uuid4(), "BTC", ForecastHorizon.MINUTES_15, TEN, Decimal(100), Decimal(101), 7, False))
    return repository


def test_every_tenant_planned_gets_the_actual_prices_of_its_forecasts() -> None:
    anna, bruno, carla = TenantId.new(), TenantId.new(), TenantId.new()
    forecasts = {anna: expired_forecasts(), bruno: expired_forecasts(), carla: expired_forecasts()}
    prices = FakePriceHistoryAdapter(prices={"BTC": Decimal(102)})
    use_case = RecordActualPricesOfTenantsUseCase(prices, lambda: {anna, bruno}, forecasts.__getitem__)

    use_case.execute(RecordActualPricesCommand(TEN + timedelta(minutes=15)))

    assert [forecasts[tenant].forecasts[0].actual_price for tenant in (anna, bruno, carla)] == [
        Decimal(102),
        Decimal(102),
        None,
    ]
