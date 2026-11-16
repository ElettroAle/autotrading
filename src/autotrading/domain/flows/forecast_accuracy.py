from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from decimal import Decimal

from autotrading.domain.flows.evaluated_forecast import EvaluatedForecast
from autotrading.domain.flows.statistics_period import TimeWindow

PERCENT_PLACES = Decimal("0.01")


@dataclass(frozen=True, slots=True)
class ForecastAccuracy:
    """How much the forecasts of a flow for one asset and horizon missed over a period (R3.6.1).

    A forecast counts in the period its horizon expires in. The means are over the evaluated forecasts, those with
    their actual price; the others are counted as not evaluable. Without an evaluated forecast the means are not
    available.
    """

    asset: str
    horizon_minutes: int
    mean_absolute_error: Decimal | None
    mean_percent_error: Decimal | None
    evaluated: int
    unevaluable: int

    @classmethod
    def per_asset_and_horizon(
        cls, forecasts: Iterable[EvaluatedForecast], window: TimeWindow
    ) -> tuple[ForecastAccuracy, ...]:
        """One error for every asset and horizon the flow forecast, in their order, even without forecasts in the
        period.
        """
        expired = list(forecasts)
        pairs = sorted({(forecast.asset, forecast.horizon_minutes) for forecast in expired})
        return tuple(
            cls._of(asset, horizon, [forecast for forecast in expired if _belongs(forecast, asset, horizon, window)])
            for asset, horizon in pairs
        )

    @classmethod
    def _of(cls, asset: str, horizon_minutes: int, forecasts: Sequence[EvaluatedForecast]) -> ForecastAccuracy:
        absolute = [forecast.absolute_error for forecast in forecasts if forecast.absolute_error is not None]
        percent = [forecast.percent_error for forecast in forecasts if forecast.percent_error is not None]
        mean_percent = _mean(percent)
        return cls(
            asset=asset,
            horizon_minutes=horizon_minutes,
            mean_absolute_error=_mean(absolute),
            mean_percent_error=None if mean_percent is None else mean_percent.quantize(PERCENT_PLACES),
            evaluated=len(absolute),
            unevaluable=len(forecasts) - len(absolute),
        )


def _belongs(forecast: EvaluatedForecast, asset: str, horizon_minutes: int, window: TimeWindow) -> bool:
    return (forecast.asset, forecast.horizon_minutes) == (asset, horizon_minutes) and window.contains(
        forecast.expires_at
    )


def _mean(values: Sequence[Decimal]) -> Decimal | None:
    if not values:
        return None
    return sum(values, Decimal(0)) / len(values)
