from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from autotrading.application.flows.errors import CycleFlowNotFoundError, CycleNotFoundError
from autotrading.application.flows.read_cycle import ReadCycleCommand, ReadCycleUseCase
from autotrading.domain.flows.cycle_record import CycleOutcome, CycleRecord
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


def test_a_cycle_is_read_with_everything_recorded(
    history: InMemoryCycleRepositoryAdapter, directory: FakeFlowDirectoryAdapter
) -> None:
    record_cycles(history, 3)

    record = ReadCycleUseCase(directory, history).execute(ReadCycleCommand(FLOW, FIRST + timedelta(minutes=1)))

    assert record == CycleRecord(FLOW, FIRST + timedelta(minutes=1), CycleOutcome.COMPLETED)


def test_a_cycle_never_recorded_is_not_found(
    history: InMemoryCycleRepositoryAdapter, directory: FakeFlowDirectoryAdapter
) -> None:
    with pytest.raises(CycleNotFoundError) as raised:
        ReadCycleUseCase(directory, history).execute(ReadCycleCommand(FLOW, FIRST))

    assert raised.value.status_code == 404
    assert str(raised.value) == "ciclo non trovato"


def test_a_flow_of_another_tenant_does_not_exist(
    history: InMemoryCycleRepositoryAdapter, directory: FakeFlowDirectoryAdapter
) -> None:
    other = uuid4()
    record_cycles(history, 1, other)

    with pytest.raises(CycleFlowNotFoundError) as raised:
        ReadCycleUseCase(directory, history).execute(ReadCycleCommand(other, FIRST))

    assert raised.value.status_code == 404
    assert str(raised.value) == "flusso non trovato"
