from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from autotrading.application.flows.errors import CycleFlowNotFoundError
from autotrading.application.flows.ports import DecisionHistoryPort, FlowDirectoryPort
from autotrading.domain.flows.decision_filter import DecisionFilter
from autotrading.domain.flows.decision_page import DECISIONS_PER_PAGE, DecisionPage
from autotrading.domain.flows.page_number import PageNumber
from autotrading.domain.flows.statistics_period import StatisticsPeriod, StatisticsPeriodKind


@dataclass(frozen=True, slots=True)
class ListDecisionsCommand:
    """The flow, the page, the filter and the period of the page of the flow (ADR periodo-al-minuto)."""

    flow_id: UUID
    page: int = 1
    criteria: DecisionFilter = field(default_factory=DecisionFilter)
    period: StatisticsPeriod = field(default_factory=lambda: StatisticsPeriod(StatisticsPeriodKind.ALL))


class ListDecisionsUseCase:
    """The decisions of the completed cycles of a flow of the tenant in the period, one by cycle and asset, from the
    most recent, that match the filter, in the pages of the cycles, with how many match in all (R6.5.5).
    """

    def __init__(self, flows: FlowDirectoryPort, history: DecisionHistoryPort, clock: Callable[[], datetime]) -> None:
        self._flows = flows
        self._history = history
        self._clock = clock

    def execute(self, command: ListDecisionsCommand) -> DecisionPage:
        number = PageNumber(command.page)
        if not self._flows.exists(command.flow_id):
            raise CycleFlowNotFoundError
        window = command.period.window(self._clock())
        # One decision more than the page tells whether another page follows.
        found = self._history.decisions_matching(
            command.flow_id, command.criteria, window, number.offset(DECISIONS_PER_PAGE), DECISIONS_PER_PAGE + 1
        )
        total = self._history.decisions_count(command.flow_id, command.criteria, window)
        return DecisionPage(number.value, tuple(found[:DECISIONS_PER_PAGE]), len(found) > DECISIONS_PER_PAGE, total)
