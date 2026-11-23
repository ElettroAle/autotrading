import logging
from collections.abc import Iterator
from contextlib import AbstractContextManager
from dataclasses import replace
from decimal import Decimal
from uuid import UUID

import pytest

from autotrading.application.flows.errors import CycleInProgressError, FlowKeyExpiredError, FlowNotActiveError
from autotrading.application.flows.ports import RiskReview
from autotrading.application.flows.run_cycle import RunCycleCommand, RunCycleUseCase
from autotrading.domain.flows.call_cost import CallCost
from autotrading.domain.flows.cycle_record import AbsentSource, CycleFailure, CycleOutcome, CycleRecord
from autotrading.domain.flows.cycle_step import CycleStep
from autotrading.domain.flows.cycle_trigger import CycleTrigger
from tests.fakes.cycles import ACTIVE, PAUSED, FakePermanentError, FakeTransientError
from tests.support.cycles import Cycles, at


@pytest.fixture
def cycles() -> Iterator[Cycles]:
    world = Cycles()
    world.add_flow("alfa", anchor="10:22:00")
    yield world
    world.release()


def run(cycles: Cycles, started: str = "10:22:00") -> CycleRecord | None:
    cycles.clock.current = at(started)
    command = RunCycleCommand(cycles.id_of("alfa"), cycles.flow("alfa").schedule, at("10:22:00"))
    return cycles.run_cycle().execute(command)


def test_a_completed_cycle_runs_every_step_and_is_recorded(cycles: Cycles) -> None:
    record = run(cycles)

    assert record is not None
    assert (record.flow_id, record.planned_at, record.outcome) == (
        cycles.id_of("alfa"),
        at("10:22:00"),
        CycleOutcome.COMPLETED,
    )
    assert (record.started_at, record.delay_seconds, record.steps) == (at("10:22:00"), None, tuple(CycleStep))
    assert cycles.records.records == [record]


def test_a_completed_cycle_records_what_every_step_produced(cycles: Cycles) -> None:
    cycles.agent.decisions[cycles.id_of("alfa")] = ["BTC"]

    record = run(cycles)

    assert record is not None
    assert [document.step for document in record.documents] == list(CycleStep)[:-1]
    assert record.document(CycleStep.READ_FLOW_STATE) == described(
        CycleStep.READ_FLOW_STATE, {"flow": "alfa", "positions": []}
    )
    assert record.document(CycleStep.COLLECT_SOURCES) == described(CycleStep.COLLECT_SOURCES, [])
    assert record.document(CycleStep.AGENT_DECISION) == described(CycleStep.AGENT_DECISION, ["BTC"])
    assert record.document(CycleStep.RISK_CHECK) == described(
        CycleStep.RISK_CHECK, RiskReview(("BTC",), {"BTC": "approvata"})
    )
    assert record.document(CycleStep.ORDER_EXECUTION) == described(
        CycleStep.ORDER_EXECUTION, [{"order": "BTC", "filled": True}]
    )
    assert record.document(CycleStep.UPDATE_FLOW_STATE) == described(
        CycleStep.UPDATE_FLOW_STATE, {"flow": "alfa", "executions": 1}
    )


def test_a_completed_cycle_records_the_cost_of_the_model_call(cycles: Cycles) -> None:
    cycles.journal.cost = CallCost(2000, 500, Decimal("0.0031"))

    record = run(cycles)

    assert record is not None
    assert record.cost == CallCost(2000, 500, Decimal("0.0031"))


def test_a_failed_cycle_records_what_it_produced_up_to_the_error(cycles: Cycles) -> None:
    cycles.failures.fail_once(cycles.id_of("alfa"), CycleStep.AGENT_DECISION, FakeTransientError("timeout"))

    record = run(cycles)

    assert record is not None
    assert [document.step for document in record.documents] == [
        CycleStep.READ_FLOW_STATE,
        CycleStep.COLLECT_SOURCES,
        CycleStep.COMPOSE_CONTEXT,
    ]
    assert record.document(CycleStep.AGENT_DECISION) is None
    assert record.cost is None


def described(step: CycleStep, result: object) -> dict[str, object]:
    return {"step": step.value, "result": repr(result)}


def test_the_cycle_carries_the_data_from_step_to_step(cycles: Cycles) -> None:
    flow_id = cycles.id_of("alfa")
    cycles.flow("alfa").positions.add("SOL")
    cycles.agent.decisions[flow_id] = ["BTC"]

    run(cycles)

    composed = cycles.context.composed[flow_id]
    assert composed.snapshot.state == {"flow": "alfa", "positions": ["SOL"]}
    assert cycles.agent.contexts == [composed]
    assert cycles.risk.snapshots == [composed.snapshot]
    assert cycles.orders.sent == [(flow_id, at("10:22:00"), "BTC")]
    assert cycles.flows.updates == [(flow_id, [{"order": "BTC", "filled": True}])]


def test_a_late_cycle_records_its_delay(cycles: Cycles) -> None:
    record = run(cycles, started="10:23:30")

    assert record is not None
    assert (record.started_at, record.delay_seconds) == (at("10:23:30"), 90)


def test_a_planned_instant_already_claimed_is_not_run_again(cycles: Cycles) -> None:
    run(cycles)

    assert run(cycles) is None
    assert len(cycles.records.records) == 1


def test_a_cycle_planned_while_the_previous_runs_is_skipped(cycles: Cycles) -> None:
    with cycles.lock.hold(cycles.id_of("alfa")):
        record = run(cycles)

    assert record == CycleRecord.skipped(cycles.id_of("alfa"), at("10:22:00"))
    assert cycles.records.records == [record]
    assert cycles.agent.calls == []


@pytest.mark.parametrize("status", [PAUSED, "fermo", "archiviato"])
def test_a_cycle_of_a_flow_no_longer_active_does_nothing_and_leaves_no_trace(cycles: Cycles, status: str) -> None:
    cycles.agent.decisions[cycles.id_of("alfa")] = ["BTC"]
    cycles.flow("alfa").status = status

    assert run(cycles) is None
    assert (cycles.flows.reads, cycles.agent.calls, cycles.orders.sent) == ([], [], [])
    assert (cycles.records.records, cycles.failure_notices.told, cycles.equity.recorded) == ([], [], [])
    assert cycles.flow("alfa").status == status


def test_a_flow_stopped_while_its_previous_cycle_runs_records_no_skipped_cycle(cycles: Cycles) -> None:
    cycles.flow("alfa").status = "fermo"
    with cycles.lock.hold(cycles.id_of("alfa")):
        record = run(cycles)

    assert record is None
    assert cycles.records.records == []


class StopAtTheLockAdapter:
    """The lock of the flow, with a stop that saves its status just before the cycle takes the lock."""

    def __init__(self, cycles: Cycles) -> None:
        self._cycles = cycles

    def hold(self, flow_id: UUID) -> AbstractContextManager[bool]:
        self._cycles.flow("alfa").status = "fermo"
        return self._cycles.lock.hold(flow_id)


def test_the_status_is_read_once_the_flow_is_held(cycles: Cycles) -> None:
    guards = replace(cycles.guards(), lock=StopAtTheLockAdapter(cycles))
    command = RunCycleCommand(cycles.id_of("alfa"), cycles.flow("alfa").schedule, at("10:22:00"))

    assert RunCycleUseCase(cycles.graph(), guards, cycles.equity, cycles.notices).execute(command) is None
    assert (cycles.flows.reads, cycles.agent.calls, cycles.records.records) == ([], [], [])


def test_the_lock_is_released_after_the_cycle(cycles: Cycles) -> None:
    run(cycles)

    with cycles.lock.hold(cycles.id_of("alfa")) as acquired:
        assert acquired


def test_the_absent_sources_are_recorded(cycles: Cycles) -> None:
    cycles.flow("alfa").sources = ("notizie",)
    cycles.sources.failing["notizie"] = FakeTransientError("fonte giù")

    record = run(cycles)

    assert record is not None
    assert record.absent_sources == (AbsentSource("notizie", "fonte giù", "RSS"),)
    assert cycles.context.composed[cycles.id_of("alfa")].absent == record.absent_sources


def test_the_sources_wait_follows_the_interval(cycles: Cycles) -> None:
    cycles.set_interval("alfa", 2)
    cycles.flow("alfa").sources = ("notizie",)
    cycles.sources.late["notizie"] = 40

    record = run(cycles)

    assert record is not None
    assert record.absent_sources == (AbsentSource("notizie", "nessuna risposta entro 30 secondi", "RSS"),)


# A source that fails is absent, never a failed cycle (R1.2.5); the record of the cycle closes it.
FAILING_STEPS = [step for step in CycleStep if step not in {CycleStep.COLLECT_SOURCES, CycleStep.RECORD_CYCLE}]


@pytest.mark.parametrize("step", FAILING_STEPS)
def test_a_transient_error_fails_the_cycle_at_its_step(cycles: Cycles, step: CycleStep) -> None:
    flow_id = cycles.id_of("alfa")
    cycles.agent.decisions[flow_id] = ["BTC"]
    cycles.failures.fail_always(flow_id, step, FakeTransientError("timeout"))

    record = run(cycles)

    steps = list(CycleStep)
    assert record is not None
    assert record.outcome is CycleOutcome.FAILED
    assert record.steps == tuple(steps[: steps.index(step)])
    assert record.failure == CycleFailure(step, "FakeTransientError", "timeout")
    assert cycles.records.records == [record]
    assert cycles.flow("alfa").status == ACTIVE


def test_no_order_follows_the_one_that_fails(cycles: Cycles) -> None:
    cycles.agent.decisions[cycles.id_of("alfa")] = ["BTC", "ETH"]
    cycles.orders.unanswered.add("BTC")

    run(cycles)

    assert cycles.orders.sent == []
    assert cycles.flows.updates == []


def test_a_permanent_error_pauses_the_flows_and_is_raised(cycles: Cycles) -> None:
    error = FakePermanentError("credito esaurito presso openrouter", provider="openrouter")
    cycles.failures.fail_once(cycles.id_of("alfa"), CycleStep.AGENT_DECISION, error)

    with pytest.raises(FakePermanentError) as raised:
        run(cycles)

    assert raised.value is error
    record = cycles.last_record("alfa")
    assert record.failure == CycleFailure(CycleStep.AGENT_DECISION, "FakePermanentError", str(error))
    assert (cycles.flow("alfa").status, cycles.flow("alfa").pause_reason) == (PAUSED, str(error))


def test_a_defect_is_neither_recorded_nor_hidden(cycles: Cycles) -> None:
    command = RunCycleCommand(cycles.id_of("alfa"), cycles.flow("alfa").schedule, at("10:22:00"))
    cycles.flows.flows.clear()

    with pytest.raises(KeyError):
        cycles.run_cycle().execute(command)
    assert cycles.records.records == []


def test_every_recorded_cycle_is_logged(cycles: Cycles, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO, logger="autotrading.cycles")
    cycles.failures.fail_always(cycles.id_of("alfa"), CycleStep.RISK_CHECK, FakeTransientError("timeout"))

    run(cycles)

    [entry] = caplog.records
    assert entry.message == "ciclo registrato"
    assert entry.__dict__["flow_id"] == str(cycles.id_of("alfa"))
    assert entry.__dict__["planned_at"] == at("10:22:00").isoformat()
    assert entry.__dict__["outcome"] == CycleOutcome.FAILED


def test_a_failed_cycle_is_told_to_the_user_with_its_message(cycles: Cycles) -> None:
    flow_id = cycles.id_of("alfa")
    cycles.failures.fail_once(flow_id, CycleStep.AGENT_DECISION, FakeTransientError("timeout"))

    run(cycles)

    assert cycles.failure_notices.told == [(flow_id, "timeout")]


def test_a_completed_cycle_is_not_told(cycles: Cycles) -> None:
    run(cycles)

    assert cycles.failure_notices.told == []


def test_a_transient_error_asks_for_the_pause_after_consecutive_failures_once_told(cycles: Cycles) -> None:
    flow_id = cycles.id_of("alfa")
    error = FakeTransientError("timeout")
    cycles.failures.fail_once(flow_id, CycleStep.AGENT_DECISION, error)

    run(cycles)

    assert cycles.consecutive_failures.asked == [(flow_id, error)]
    assert cycles.consecutive_failures.told_before == [[(flow_id, "timeout")]]


def test_a_permanent_error_does_not_count_towards_the_consecutive_failures(cycles: Cycles) -> None:
    error = FakePermanentError("credito esaurito presso openrouter", provider="openrouter")
    cycles.failures.fail_once(cycles.id_of("alfa"), CycleStep.AGENT_DECISION, error)

    with pytest.raises(FakePermanentError):
        run(cycles)

    assert cycles.consecutive_failures.asked == []


def test_a_completed_cycle_does_not_ask_for_the_pause_after_consecutive_failures(cycles: Cycles) -> None:
    run(cycles)

    assert cycles.consecutive_failures.asked == []


def test_a_completed_cycle_records_the_equity_of_the_state_at_its_end(cycles: Cycles) -> None:
    run(cycles)

    assert cycles.equity.recorded == [(cycles.id_of("alfa"), at("10:22:00"), {"flow": "alfa", "executions": 0})]


@pytest.mark.parametrize(
    "step",
    [CycleStep.COMPOSE_CONTEXT, CycleStep.AGENT_DECISION, CycleStep.ORDER_EXECUTION, CycleStep.UPDATE_FLOW_STATE],
)
def test_a_cycle_failed_after_reading_the_state_records_the_equity_of_the_state_read(
    cycles: Cycles, step: CycleStep
) -> None:
    cycles.failures.fail_always(cycles.id_of("alfa"), step, FakeTransientError("timeout"))

    run(cycles)

    assert cycles.equity.recorded == [(cycles.id_of("alfa"), at("10:22:00"), {"flow": "alfa", "positions": []})]


def test_the_equity_of_a_failed_cycle_follows_its_record(cycles: Cycles) -> None:
    cycles.failures.fail_once(cycles.id_of("alfa"), CycleStep.AGENT_DECISION, FakePermanentError("chiave revocata"))

    with pytest.raises(FakePermanentError):
        run(cycles)

    assert len(cycles.records.records) == len(cycles.equity.recorded) == 1


def test_a_cycle_failed_reading_the_state_records_no_equity(cycles: Cycles) -> None:
    cycles.failures.fail_always(cycles.id_of("alfa"), CycleStep.READ_FLOW_STATE, FakeTransientError("timeout"))

    run(cycles)

    assert cycles.records.records[0].outcome is CycleOutcome.FAILED
    assert cycles.equity.recorded == []


def test_a_skipped_cycle_records_no_equity(cycles: Cycles) -> None:
    with cycles.lock.hold(cycles.id_of("alfa")):
        run(cycles)

    assert cycles.equity.recorded == []


def run_on_demand(cycles: Cycles) -> CycleRecord | None:
    cycles.clock.current = at("10:40:00")
    command = RunCycleCommand(
        cycles.id_of("alfa"), cycles.flow("alfa").schedule, at("10:40:00"), CycleTrigger.ON_DEMAND
    )
    return cycles.run_cycle().execute(command)


def test_a_planned_cycle_is_recorded_as_planned(cycles: Cycles) -> None:
    record = run(cycles)

    assert record is not None
    assert record.trigger is CycleTrigger.SCHEDULED


def test_a_cycle_asked_for_now_runs_every_step_and_is_recorded_as_asked(cycles: Cycles) -> None:
    record = run_on_demand(cycles)

    assert record is not None
    assert (record.planned_at, record.outcome, record.steps) == (
        at("10:40:00"),
        CycleOutcome.COMPLETED,
        tuple(CycleStep),
    )
    assert record.trigger is CycleTrigger.ON_DEMAND
    assert cycles.records.records == [record]


@pytest.mark.parametrize("status", [PAUSED, "fermo"])
def test_a_cycle_asked_for_now_on_a_flow_not_active_is_refused(cycles: Cycles, status: str) -> None:
    cycles.flow("alfa").status = status

    with pytest.raises(FlowNotActiveError):
        run_on_demand(cycles)

    assert (cycles.flows.reads, cycles.agent.calls, cycles.records.records) == ([], [], [])


def test_a_cycle_asked_for_now_while_another_runs_is_refused_and_not_recorded_as_skipped(cycles: Cycles) -> None:
    with cycles.lock.hold(cycles.id_of("alfa")), pytest.raises(CycleInProgressError):
        run_on_demand(cycles)

    assert (cycles.agent.calls, cycles.records.records, cycles.equity.recorded) == ([], [], [])


def test_a_permanent_error_of_a_cycle_asked_for_now_pauses_the_flows_and_is_raised(cycles: Cycles) -> None:
    # Fail fast also for the cycle the user asks for: the only handler records, pauses and raises (context-flows.md).
    error = FakePermanentError("credito esaurito presso openrouter", provider="openrouter")
    cycles.failures.fail_once(cycles.id_of("alfa"), CycleStep.AGENT_DECISION, error)

    with pytest.raises(FakePermanentError) as raised:
        run_on_demand(cycles)

    assert raised.value is error
    record = cycles.last_record("alfa")
    assert record.failure == CycleFailure(CycleStep.AGENT_DECISION, "FakePermanentError", str(error))
    assert record.trigger is CycleTrigger.ON_DEMAND
    assert (cycles.flow("alfa").status, cycles.flow("alfa").pause_reason) == (PAUSED, str(error))


def test_a_flow_that_uses_an_expired_key_goes_in_pause_before_its_cycle_starts_and_leaves_no_trace(
    cycles: Cycles,
) -> None:
    """R6.2.2: the pause of a revoked key (R1.2.4), before any step reads the flow."""
    cycles.expired_keys.expired_for[cycles.id_of("alfa")] = "chiave openrouter scaduta"

    assert run(cycles) is None

    assert (cycles.flow("alfa").status, cycles.flow("alfa").pause_reason) == (PAUSED, "chiave openrouter scaduta")
    assert (cycles.flows.reads, cycles.agent.calls, cycles.records.records) == ([], [], [])


def test_a_cycle_asked_for_now_on_a_flow_with_an_expired_key_is_refused(cycles: Cycles) -> None:
    cycles.expired_keys.expired_for[cycles.id_of("alfa")] = "chiave openrouter scaduta"

    with pytest.raises(FlowKeyExpiredError) as raised:
        run_on_demand(cycles)

    assert (raised.value.status_code, str(raised.value)) == (409, "una chiave del flusso è scaduta")
    assert cycles.flow("alfa").status == PAUSED


# The notices of the cycle (ADR notifiche-del-ciclo-dopo-lo-stato-registrato): released as its last step, once its
# record and its equity are saved, so the state of the flow they end with is the one after the events they tell.


def test_a_completed_cycle_releases_its_notices_once_its_equity_is_recorded(cycles: Cycles) -> None:
    run(cycles)

    assert cycles.notices.releases == [(1, 1, 0, [])]


def test_a_failed_cycle_releases_its_notices_after_its_record_its_equity_and_its_failure(cycles: Cycles) -> None:
    cycles.failures.fail_always(cycles.id_of("alfa"), CycleStep.ORDER_EXECUTION, FakeTransientError("timeout"))

    run(cycles)

    assert cycles.notices.releases == [(1, 1, 1, [])]


def test_a_cycle_failed_reading_the_state_releases_its_notices_without_an_equity(cycles: Cycles) -> None:
    cycles.failures.fail_always(cycles.id_of("alfa"), CycleStep.READ_FLOW_STATE, FakeTransientError("timeout"))

    run(cycles)

    assert cycles.notices.releases == [(1, 0, 1, [])]


def test_a_permanent_error_releases_the_notices_after_the_pause_and_is_raised(cycles: Cycles) -> None:
    error = FakePermanentError("credito esaurito presso openrouter", provider="openrouter")
    cycles.failures.fail_once(cycles.id_of("alfa"), CycleStep.ORDER_EXECUTION, error)

    with pytest.raises(FakePermanentError):
        run(cycles)

    assert cycles.notices.releases == [(1, 1, 1, ["alfa"])]


def test_a_cycle_that_never_runs_its_steps_releases_nothing(cycles: Cycles) -> None:
    with cycles.lock.hold(cycles.id_of("alfa")):
        run(cycles)
    cycles.flow("alfa").status = PAUSED
    run(cycles)

    assert cycles.notices.releases == []
