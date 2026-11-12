from collections.abc import Sequence
from decimal import Decimal

from autotrading.domain.sources.errors import InsufficientHistoryError

MINIMUM_POINTS = 3
# A coarse grid is enough: the forecast is one input among the sources, not a trading signal by itself (ADR 0043).
SMOOTHING_GRID = tuple(step / 10 for step in range(1, 10))


def holt_forecast(prices: Sequence[Decimal], steps: Decimal) -> Decimal:
    """The price `steps` sampling intervals after the last one, by Holt's linear trend smoothing (R1.3.5).

    Level and trend smoothing are the pair of the grid with the smallest one-step error on the history itself.
    """
    if len(prices) < MINIMUM_POINTS:
        raise InsufficientHistoryError(MINIMUM_POINTS, len(prices))
    series = [float(price) for price in prices]
    alpha, beta = min(
        ((alpha, beta) for alpha in SMOOTHING_GRID for beta in SMOOTHING_GRID),
        key=lambda pair: _one_step_error(series, *pair),
    )
    level, trend = _smoothed(series, alpha, beta)
    return Decimal(repr(level + float(steps) * trend))


def _one_step_error(series: list[float], alpha: float, beta: float) -> float:
    level, trend = series[0], series[1] - series[0]
    error = 0.0
    for value in series[1:]:
        expected = level + trend
        error += (value - expected) ** 2
        level, trend = _next(value, level, trend, alpha, beta)
    return error


def _smoothed(series: list[float], alpha: float, beta: float) -> tuple[float, float]:
    level, trend = series[0], series[1] - series[0]
    for value in series[1:]:
        level, trend = _next(value, level, trend, alpha, beta)
    return level, trend


def _next(value: float, level: float, trend: float, alpha: float, beta: float) -> tuple[float, float]:
    new_level = alpha * value + (1 - alpha) * (level + trend)
    return new_level, beta * (new_level - level) + (1 - beta) * trend
