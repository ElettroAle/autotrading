from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from autotrading.application.flows.ports import CycleHistoryPort, FlowSummary, FlowSummaryPort
from autotrading.application.flows.read_flow_results import ReadFlowResultsCommand, ReadFlowResultsUseCase
from autotrading.domain.flows.cycle_record import CycleRecord
from autotrading.domain.flows.flow_results import FlowResults
from autotrading.domain.flows.flow_return import FlowReturn
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.flows.openings_suspension import OpeningsSuspension
from autotrading.domain.flows.statistics_period import StatisticsPeriod, StatisticsPeriodKind

RECENT_CYCLES = 10


@dataclass(frozen=True, slots=True)
class ListFlowOverviewsCommand:
    """The period of the results of every flow, the same periods as the statistics (ADR 0122, R6.4.2)."""

    period: str = StatisticsPeriodKind.ALL.value
    since: datetime | None = None
    until: datetime | None = None


@dataclass(frozen=True, slots=True)
class FlowOverview:
    """A flow in use as the user follows it: what it is, its recent cycles, when the next one falls and how it is doing
    (R1.7.3, R2.2.2, R6.4.2). A draft has no account yet, so neither currency, capital nor results (ADR 0124).
    """

    summary: FlowSummary
    environment: str
    recent_cycles: tuple[CycleRecord, ...]
    next_cycle_at: datetime | None
    results: FlowResults | None

    @property
    def last_cycle(self) -> CycleRecord | None:
        return self.recent_cycles[0] if self.recent_cycles else None

    @property
    def openings_suspension(self) -> OpeningsSuspension | None:
        """The suspension of the openings in force now, of any cause; a draft never has one (R3.2.2, R3.3.1)."""
        return None if self.results is None else self.results.openings_suspension

    @property
    def currency(self) -> str | None:
        return None if self.results is None else self.results.currency

    @property
    def capital(self) -> FlowReturn | None:
        return None if self.results is None else FlowReturn.of(self.results.state)


class ListFlowOverviewsUseCase:
    """The flows in use of the tenant, each with its last ten recorded cycles from the most recent, the next planned
    one, its capital from the state attributed to it and its results in the period asked for (R1.7.3, R2.2.2, R6.4.2,
    ADR 0127, ADR riepilogo-dei-risultati-nell-api).

    Only an active flow has a next cycle: a paused or stopped one plans nothing until it starts again.
    """

    def __init__(
        self,
        summaries: FlowSummaryPort,
        history: CycleHistoryPort,
        flow_results: ReadFlowResultsUseCase,
        environment: str,
        clock: Callable[[], datetime],
    ) -> None:
        self._summaries = summaries
        self._history = history
        self._flow_results = flow_results
        self._environment = environment
        self._clock = clock

    def execute(self, command: ListFlowOverviewsCommand) -> list[FlowOverview]:
        StatisticsPeriod.named(command.period, command.since, command.until)
        now = self._clock()
        return [self._overview_of(summary, command, now) for summary in self._summaries.execute()]

    def _overview_of(self, summary: FlowSummary, command: ListFlowOverviewsCommand, now: datetime) -> FlowOverview:
        recent = tuple(self._history.newest(summary.flow_id, 0, RECENT_CYCLES))
        next_cycle_at = None if summary.schedule is None else summary.schedule.next_after(now)
        if FlowStatus(summary.status) is FlowStatus.DRAFT:
            return FlowOverview(summary, self._environment, recent, next_cycle_at, None)
        results = self._flow_results.execute(
            ReadFlowResultsCommand(summary.flow_id, command.period, command.since, command.until)
        )
        return FlowOverview(summary, self._environment, recent, next_cycle_at, results)
