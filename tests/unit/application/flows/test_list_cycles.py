from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from autotrading.application.flows.errors import CycleFlowNotFoundError
from autotrading.application.flows.list_cycles import ListCyclesCommand, ListCyclesUseCase
from autotrading.domain.flows.cycle_filter import CycleFilter
from autotrading.domain.flows.cycle_record import CycleOutcome, CycleRecord
from autotrading.domain.flows.errors import InvalidPageNumberError
from autotrading.domain.flows.recorded_decision import RecordedDecision
from tests.fakes.cycles import FakeFlowDirectoryAdapter, InMemoryCycleRepositoryAdapter

FIRST = datetime(2026, 11, 12, tzinfo=UTC)
FLOW = uuid4()


@pytest.fixture
def history() -> InMemoryCycleRepositoryAdapter:
    return InMemoryCycleRepositoryAdapter()


@pytest.fixture
def directory() -> FakeFlowDirectoryAdapter:
    return FakeFlowDirectoryAdapter({FLOW})


def record_cycles(history: InMemoryCycleRepositoryAdapter, count: int, flow_id: UUID = FLOW) -> None:
    for minute in range(count):
        history.record(CycleRecord(flow_id, FIRST + timedelta(minutes=minute), CycleOutcome.COMPLETED))


def instants(records: tuple[CycleRecord, ...]) -> list[int]:
    return [int((record.planned_at - FIRST).total_seconds() // 60) for record in records]


def test_the_first_page_holds_the_fifty_most_recent_cycles(
    history: InMemoryCycleRepositoryAdapter, directory: FakeFlowDirectoryAdapter
) -> None:
    record_cycles(history, 120)

    page = ListCyclesUseCase(directory, history).execute(ListCyclesCommand(FLOW))

    assert (page.number, page.has_next) == (1, True)
    assert instants(page.cycles) == list(range(119, 69, -1))


def test_the_last_page_holds_what_remains_and_says_no_page_follows(
    history: InMemoryCycleRepositoryAdapter, directory: FakeFlowDirectoryAdapter
) -> None:
    record_cycles(history, 120)

    page = ListCyclesUseCase(directory, history).execute(ListCyclesCommand(FLOW, 3))

    assert (page.number, page.has_next) == (3, False)
    assert instants(page.cycles) == list(range(19, -1, -1))


def test_a_page_of_exactly_fifty_cycles_says_no_page_follows(
    history: InMemoryCycleRepositoryAdapter, directory: FakeFlowDirectoryAdapter
) -> None:
    record_cycles(history, 50)

    page = ListCyclesUseCase(directory, history).execute(ListCyclesCommand(FLOW))

    assert (len(page.cycles), page.has_next) == (50, False)


def test_the_cycles_of_another_flow_stay_out_of_the_page(
    history: InMemoryCycleRepositoryAdapter, directory: FakeFlowDirectoryAdapter
) -> None:
    record_cycles(history, 2)
    record_cycles(history, 3, uuid4())

    page = ListCyclesUseCase(directory, history).execute(ListCyclesCommand(FLOW))

    assert instants(page.cycles) == [1, 0]


def test_a_page_before_the_first_is_refused(
    history: InMemoryCycleRepositoryAdapter, directory: FakeFlowDirectoryAdapter
) -> None:
    with pytest.raises(InvalidPageNumberError):
        ListCyclesUseCase(directory, history).execute(ListCyclesCommand(FLOW, 0))


def test_a_flow_of_another_tenant_does_not_exist(
    history: InMemoryCycleRepositoryAdapter, directory: FakeFlowDirectoryAdapter
) -> None:
    other = uuid4()
    record_cycles(history, 1, other)

    with pytest.raises(CycleFlowNotFoundError) as raised:
        ListCyclesUseCase(directory, history).execute(ListCyclesCommand(other))

    assert raised.value.status_code == 404
    assert str(raised.value) == "flusso non trovato"


def a_cycle_deciding(minute: int, *actions: str, outcome: CycleOutcome = CycleOutcome.COMPLETED) -> CycleRecord:
    decisions = tuple(RecordedDecision.named("BTC", action, None, 50, "motivo") for action in actions)
    return CycleRecord(FLOW, FIRST + timedelta(minutes=minute), outcome, decisions=decisions)


def test_the_page_says_how_many_cycles_match_in_all(
    history: InMemoryCycleRepositoryAdapter, directory: FakeFlowDirectoryAdapter
) -> None:
    record_cycles(history, 120)

    page = ListCyclesUseCase(directory, history).execute(ListCyclesCommand(FLOW, 2))

    assert (len(page.cycles), page.total) == (50, 120)


def test_the_cycles_filtered_by_outcome_are_only_those_with_it(
    history: InMemoryCycleRepositoryAdapter, directory: FakeFlowDirectoryAdapter
) -> None:
    record_cycles(history, 3)
    history.record(CycleRecord(FLOW, FIRST + timedelta(minutes=10), CycleOutcome.FAILED))

    page = ListCyclesUseCase(directory, history).execute(
        ListCyclesCommand(FLOW, criteria=CycleFilter.named(outcome="fallito"))
    )

    assert instants(page.cycles) == [10]
    assert (page.total, page.has_next) == (1, False)


def test_the_cycles_filtered_by_decision_are_those_where_the_agent_took_it(
    history: InMemoryCycleRepositoryAdapter, directory: FakeFlowDirectoryAdapter
) -> None:
    history.record(a_cycle_deciding(0, "apri"))
    history.record(a_cycle_deciding(1, "mantieni", "chiudi"))
    history.record(a_cycle_deciding(2))
    history.record(CycleRecord(FLOW, FIRST + timedelta(minutes=3), CycleOutcome.FAILED))

    def decided(decision: str) -> list[int]:
        command = ListCyclesCommand(FLOW, criteria=CycleFilter.named(decision=decision))
        return instants(ListCyclesUseCase(directory, history).execute(command).cycles)

    assert decided("apertura") == [0]
    assert decided("chiusura") == [1]
    assert decided("mantenimento") == [1]
    assert decided("nessuna") == [3, 2]


def test_the_cycles_filtered_by_an_interval_are_those_planned_within_it(
    history: InMemoryCycleRepositoryAdapter, directory: FakeFlowDirectoryAdapter
) -> None:
    history.record(CycleRecord(FLOW, FIRST - timedelta(minutes=1), CycleOutcome.COMPLETED))
    record_cycles(history, 2)
    history.record(CycleRecord(FLOW, FIRST + timedelta(days=1), CycleOutcome.COMPLETED))

    criteria = CycleFilter.named(since=FIRST, until=FIRST + timedelta(minutes=1))
    command = ListCyclesCommand(FLOW, criteria=criteria)
    page = ListCyclesUseCase(directory, history).execute(command)

    assert (instants(page.cycles), page.total) == ([1, 0], 2)
