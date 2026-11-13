from datetime import UTC, datetime, timedelta
from uuid import uuid4

from autotrading.application.flows.list_flow_overviews import ListFlowOverviewsUseCase
from autotrading.application.flows.ports import FlowSummary
from autotrading.domain.flows.cycle_record import CycleOutcome, CycleRecord
from autotrading.domain.flows.cycle_schedule import CycleSchedule
from tests.fakes.cycles import InMemoryCycleRepositoryAdapter

STARTED = datetime(2026, 11, 12, 10, 0, tzinfo=UTC)
NOW = STARTED + timedelta(minutes=20)


class FakeFlowSummariesAdapter:
    def __init__(self, *summaries: FlowSummary) -> None:
        self.summaries = list(summaries)

    def execute(self) -> list[FlowSummary]:
        return self.summaries


def summary(status: str = "attivo", schedule: CycleSchedule | None = None) -> FlowSummary:
    return FlowSummary(uuid4(), "alfa", "test-1", status, None, "openrouter/deepseek-chat", schedule)


def overviews_of(history: InMemoryCycleRepositoryAdapter, *summaries: FlowSummary) -> ListFlowOverviewsUseCase:
    return ListFlowOverviewsUseCase(FakeFlowSummariesAdapter(*summaries), history, "dev", lambda: NOW)


def test_an_active_flow_shows_its_last_cycle_and_the_next_planned_one() -> None:
    history = InMemoryCycleRepositoryAdapter()
    active = summary(schedule=CycleSchedule(STARTED, timedelta(minutes=15)))
    history.record(CycleRecord(active.flow_id, STARTED, CycleOutcome.COMPLETED))
    last = CycleRecord(active.flow_id, STARTED + timedelta(minutes=15), CycleOutcome.FAILED)
    history.record(last)

    [overview] = overviews_of(history, active).execute()

    assert (overview.summary, overview.environment) == (active, "dev")
    assert overview.last_cycle == last
    assert overview.next_cycle_at == STARTED + timedelta(minutes=30)


def test_a_flow_without_schedule_nor_cycles_has_neither_last_nor_next_cycle() -> None:
    paused = summary(status="in pausa")

    [overview] = overviews_of(InMemoryCycleRepositoryAdapter(), paused).execute()

    assert (overview.last_cycle, overview.next_cycle_at) == (None, None)
