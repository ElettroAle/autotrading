from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from autotrading.application.flows.ports import CycleHistoryPort, FlowSummary, FlowSummaryPort
from autotrading.domain.flows.cycle_record import CycleRecord


@dataclass(frozen=True, slots=True)
class FlowOverview:
    """A flow in use as the user follows it: what it is, its last cycle and when the next one falls (R1.7.3)."""

    summary: FlowSummary
    environment: str
    last_cycle: CycleRecord | None
    next_cycle_at: datetime | None


class ListFlowOverviewsUseCase:
    """The flows in use of the tenant, each with its last recorded cycle and the next planned one (R1.7.3).

    Only an active flow has a next cycle: a paused or stopped one plans nothing until it starts again.
    """

    def __init__(
        self, summaries: FlowSummaryPort, history: CycleHistoryPort, environment: str, clock: Callable[[], datetime]
    ) -> None:
        self._summaries = summaries
        self._history = history
        self._environment = environment
        self._clock = clock

    def execute(self) -> list[FlowOverview]:
        now = self._clock()
        return [self._overview_of(summary, now) for summary in self._summaries.execute()]

    def _overview_of(self, summary: FlowSummary, now: datetime) -> FlowOverview:
        newest = self._history.newest(summary.flow_id, 0, 1)
        next_cycle_at = None if summary.schedule is None else summary.schedule.next_after(now)
        return FlowOverview(summary, self._environment, newest[0] if newest else None, next_cycle_at)
