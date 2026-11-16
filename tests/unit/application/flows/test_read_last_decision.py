from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from autotrading.application.flows.errors import CycleFlowNotFoundError
from autotrading.application.flows.read_last_decision import ReadLastDecisionCommand, ReadLastDecisionUseCase
from autotrading.domain.flows.cycle_record import CycleFailure, CycleOutcome, CycleRecord
from autotrading.domain.flows.cycle_step import CycleStep
from autotrading.domain.flows.recorded_decision import DecidedCycle, DecisionAction, RecordedDecision
from autotrading.domain.flows.trade_side import TradeSide
from tests.fakes.cycles import FakeFlowDirectoryAdapter, InMemoryCycleRepositoryAdapter

TEN = datetime(2026, 11, 16, 10, 0, tzinfo=UTC)
FLOW = uuid4()
OPENING = RecordedDecision("BTC", DecisionAction.OPEN, TradeSide.LONG, 72, "trend rialzista")
HOLDING = RecordedDecision("BTC", DecisionAction.HOLD, None, 40, "attesa")


@pytest.fixture
def history() -> InMemoryCycleRepositoryAdapter:
    return InMemoryCycleRepositoryAdapter()


def use_case(history: InMemoryCycleRepositoryAdapter) -> ReadLastDecisionUseCase:
    return ReadLastDecisionUseCase(FakeFlowDirectoryAdapter({FLOW}), history)


def a_cycle(hours: int, *decisions: RecordedDecision, outcome: CycleOutcome = CycleOutcome.COMPLETED) -> CycleRecord:
    return CycleRecord(FLOW, TEN + timedelta(hours=hours), outcome, decisions=decisions)


def test_the_last_decision_is_that_of_the_most_recent_completed_cycle(history: InMemoryCycleRepositoryAdapter) -> None:
    history.record(a_cycle(-1, HOLDING))
    history.record(a_cycle(0, OPENING))

    assert use_case(history).execute(ReadLastDecisionCommand(FLOW)) == DecidedCycle(TEN, (OPENING,))


def test_a_cycle_failed_after_the_last_decision_leaves_it_in_place(history: InMemoryCycleRepositoryAdapter) -> None:
    history.record(a_cycle(0, OPENING))
    failure = CycleFailure(CycleStep.AGENT_DECISION, "ModelUnavailableError", "timeout")
    history.record(CycleRecord(FLOW, TEN + timedelta(hours=1), CycleOutcome.FAILED, failure=failure))
    history.record(a_cycle(2, HOLDING, outcome=CycleOutcome.FAILED))

    assert use_case(history).execute(ReadLastDecisionCommand(FLOW)) == DecidedCycle(TEN, (OPENING,))


def test_a_completed_cycle_without_decisions_leaves_the_last_decision_in_place(
    history: InMemoryCycleRepositoryAdapter,
) -> None:
    history.record(a_cycle(0, OPENING))
    history.record(a_cycle(1))

    assert use_case(history).execute(ReadLastDecisionCommand(FLOW)) == DecidedCycle(TEN, (OPENING,))


def test_a_flow_without_completed_cycles_has_no_decision(history: InMemoryCycleRepositoryAdapter) -> None:
    history.record(CycleRecord.skipped(FLOW, TEN))

    assert use_case(history).execute(ReadLastDecisionCommand(FLOW)) is None


def test_the_flow_of_another_tenant_is_not_found(history: InMemoryCycleRepositoryAdapter) -> None:
    with pytest.raises(CycleFlowNotFoundError) as raised:
        use_case(history).execute(ReadLastDecisionCommand(uuid4()))

    assert raised.value.status_code == 404
