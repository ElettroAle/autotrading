from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from autotrading.application.flows.ports import CycleHistoryPort, FlowSummary, FlowSummaryPort
from autotrading.application.flows.read_flow_state import ReadFlowStateCommand, ReadFlowStateUseCase
from autotrading.domain.flows.cycle_record import CycleRecord
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.flow_return import FlowReturn
from autotrading.domain.flows.flow_status import FlowStatus

RECENT_CYCLES = 10


@dataclass(frozen=True, slots=True)
class FlowOverview:
    """A flow in use as the user follows it: what it is, its recent cycles, when the next one falls and how its
    capital is doing (R1.7.3, R2.2.2). A draft has no account yet, so neither currency nor capital (ADR 0124).
    """

    summary: FlowSummary
    environment: str
    recent_cycles: tuple[CycleRecord, ...]
    next_cycle_at: datetime | None
    currency: str | None
    capital: FlowReturn | None

    @property
    def last_cycle(self) -> CycleRecord | None:
        return self.recent_cycles[0] if self.recent_cycles else None


class ListFlowOverviewsUseCase:
    """The flows in use of the tenant, each with its last ten recorded cycles from the most recent, the next planned
    one and its capital from the state attributed to it (R1.7.3, R2.2.2, ADR 0127).

    Only an active flow has a next cycle: a paused or stopped one plans nothing until it starts again.
    """

    def __init__(
        self,
        summaries: FlowSummaryPort,
        history: CycleHistoryPort,
        flow_state: ReadFlowStateUseCase,
        environment: str,
        clock: Callable[[], datetime],
    ) -> None:
        self._summaries = summaries
        self._history = history
        self._flow_state = flow_state
        self._environment = environment
        self._clock = clock

    def execute(self) -> list[FlowOverview]:
        now = self._clock()
        return [self._overview_of(summary, now) for summary in self._summaries.execute()]

    def _overview_of(self, summary: FlowSummary, now: datetime) -> FlowOverview:
        recent = tuple(self._history.newest(summary.flow_id, 0, RECENT_CYCLES))
        next_cycle_at = None if summary.schedule is None else summary.schedule.next_after(now)
        if FlowStatus(summary.status) is FlowStatus.DRAFT:
            return FlowOverview(summary, self._environment, recent, next_cycle_at, None, None)
        state = self._flow_state.execute(ReadFlowStateCommand(FlowId(summary.flow_id)))
        return FlowOverview(summary, self._environment, recent, next_cycle_at, state.currency, FlowReturn.of(state))
