from datetime import datetime

from autotrading.domain.sources.price_forecast import PriceForecast


class InMemoryForecastRepositoryAdapter:
    """The forecasts of one tenant, as the database records them."""

    def __init__(self) -> None:
        self.forecasts: list[PriceForecast] = []

    def add(self, forecast: PriceForecast) -> None:
        self.forecasts.append(forecast)

    def expired_without_actual(self, now: datetime) -> list[PriceForecast]:
        return [kept for kept in self.forecasts if kept.actual_price is None and kept.expires_at <= now]

    def record_actual(self, forecast: PriceForecast) -> None:
        self.forecasts = [forecast if _key(kept) == _key(forecast) else kept for kept in self.forecasts]


def _key(forecast: PriceForecast) -> tuple[object, ...]:
    return forecast.flow_id, forecast.asset, forecast.horizon, forecast.made_at
