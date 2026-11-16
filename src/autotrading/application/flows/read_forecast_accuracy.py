from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from autotrading.application.flows.ports import FlowForecastsPort, FlowRepositoryPort
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.forecast_accuracy import ForecastAccuracy
from autotrading.domain.flows.statistics_period import StatisticsPeriod, StatisticsPeriodKind


@dataclass(frozen=True, slots=True)
class ReadForecastAccuracyCommand:
    flow_id: UUID
    period: str = StatisticsPeriodKind.ALL.value
    since: datetime | None = None
    until: datetime | None = None


class ReadForecastAccuracyUseCase:
    """The mean error of the forecasts of a flow of the tenant over a period, by asset and horizon (R3.6.1)."""

    def __init__(self, flows: FlowRepositoryPort, forecasts: FlowForecastsPort, clock: Callable[[], datetime]) -> None:
        self._flows = flows
        self._forecasts = forecasts
        self._clock = clock

    def execute(self, command: ReadForecastAccuracyCommand) -> tuple[ForecastAccuracy, ...]:
        period = StatisticsPeriod.named(command.period, command.since, command.until)
        flow = self._flows.get(FlowId(command.flow_id))
        now = self._clock()
        expired = self._forecasts.expired_forecasts(flow.id, now)
        return ForecastAccuracy.per_asset_and_horizon(expired, period.window(now))
