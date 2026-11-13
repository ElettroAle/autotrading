from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from autotrading.application.flows.errors import CycleFlowNotFoundError
from autotrading.application.flows.read_flow_cost import ReadFlowCostCommand, ReadFlowCostUseCase
from autotrading.domain.flows.call_cost import CallCost
from autotrading.domain.flows.cycle_record import CycleOutcome, CycleRecord
from autotrading.domain.flows.flow_cost import DailyCost, FlowCost
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


def test_the_cost_of_a_flow_adds_the_cost_of_its_cycles(
    history: InMemoryCycleRepositoryAdapter, directory: FakeFlowDirectoryAdapter
) -> None:
    for minute, amount in enumerate(("0.01", "0.02")):
        history.record(
            CycleRecord(
                FLOW, FIRST + timedelta(minutes=minute), CycleOutcome.COMPLETED, cost=CallCost(1, 1, Decimal(amount))
            )
        )
    history.record(CycleRecord(FLOW, FIRST + timedelta(minutes=5), CycleOutcome.SKIPPED))

    cost = ReadFlowCostUseCase(directory, history).execute(ReadFlowCostCommand(FLOW))

    assert cost == FlowCost(Decimal("0.03"), (DailyCost(FIRST.date(), Decimal("0.03")),), 0)


def test_a_flow_of_another_tenant_does_not_exist(
    history: InMemoryCycleRepositoryAdapter, directory: FakeFlowDirectoryAdapter
) -> None:
    other = uuid4()
    record_cycles(history, 1, other)

    with pytest.raises(CycleFlowNotFoundError) as raised:
        ReadFlowCostUseCase(directory, history).execute(ReadFlowCostCommand(other))

    assert raised.value.status_code == 404
    assert str(raised.value) == "flusso non trovato"
