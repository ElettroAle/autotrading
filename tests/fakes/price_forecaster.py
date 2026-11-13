from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal

from autotrading.application.sources.errors import SourceUnavailableError
from autotrading.domain.sources.forecast import FORECAST
from autotrading.domain.sources.price_forecast import ForecastHorizon, PriceHistory


@dataclass
class FakePriceForecasterAdapter:
    """A forecaster that predicts the last price plus one hundredth per minute of horizon, or does not answer."""

    missing: set[str] = field(default_factory=set)
    requests: list[tuple[str, int, tuple[ForecastHorizon, ...]]] = field(default_factory=list)

    def predict(
        self, asset: str, history: PriceHistory, horizons: tuple[ForecastHorizon, ...]
    ) -> Mapping[ForecastHorizon, Decimal]:
        self.requests.append((asset, history.requested_days, horizons))
        if asset in self.missing:
            raise SourceUnavailableError(FORECAST.name)
        return {horizon: history.last_price + Decimal(horizon.minutes) / 100 for horizon in horizons}
