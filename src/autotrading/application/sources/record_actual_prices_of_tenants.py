from collections.abc import Callable, Iterable

from autotrading.application.sources.ports import ForecastRepositoryPort, PriceHistoryPort
from autotrading.application.sources.record_actual_prices import RecordActualPricesCommand, RecordActualPricesUseCase
from autotrading.domain.tenancy.tenant_id import TenantId


class RecordActualPricesOfTenantsUseCase:
    """The actual price beside every expired forecast of the tenants the worker plans for (R1.3.5)."""

    def __init__(
        self,
        prices: PriceHistoryPort,
        tenants: Callable[[], Iterable[TenantId]],
        forecasts_of: Callable[[TenantId], ForecastRepositoryPort],
    ) -> None:
        self._prices = prices
        self._tenants = tenants
        self._forecasts_of = forecasts_of

    def execute(self, command: RecordActualPricesCommand) -> None:
        for tenant_id in self._tenants():
            RecordActualPricesUseCase(self._prices, self._forecasts_of(tenant_id)).execute(command)
