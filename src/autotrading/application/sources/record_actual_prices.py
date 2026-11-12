import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from autotrading.application.sources.errors import SourceUnavailableError
from autotrading.application.sources.ports import ForecastRepositoryPort, PriceHistoryPort
from autotrading.domain.sources.price_forecast import PriceForecast

operations = logging.getLogger("autotrading.sources")


@dataclass(frozen=True, slots=True)
class RecordActualPricesCommand:
    now: datetime


class RecordActualPricesUseCase:
    """Records the actual price next to every forecast whose horizon has expired (R1.3.5)."""

    def __init__(self, prices: PriceHistoryPort, forecasts: ForecastRepositoryPort) -> None:
        self._prices = prices
        self._forecasts = forecasts

    def execute(self, command: RecordActualPricesCommand) -> list[PriceForecast]:
        expired = self._forecasts.expired_without_actual(command.now)
        current = self._current_prices({forecast.asset for forecast in expired})
        recorded = [forecast.with_actual(current[forecast.asset]) for forecast in expired if forecast.asset in current]
        for forecast in recorded:
            self._forecasts.record_actual(forecast)
        return recorded

    def _current_prices(self, assets: set[str]) -> dict[str, Decimal]:
        prices: dict[str, Decimal] = {}
        for asset in sorted(assets):
            try:
                prices[asset] = self._prices.current_price(asset)
            except SourceUnavailableError:
                # The forecast stays without its actual price and is taken again at the next run.
                operations.warning("prezzo effettivo non disponibile", extra={"asset": asset})
        return prices
