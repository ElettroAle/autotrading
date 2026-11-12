import logging
from collections.abc import Iterator
from decimal import Decimal

import pytest

from autotrading.application.cycles.ports import RiskReview
from autotrading.application.cycles.run_cycle import RunCycleCommand
from autotrading.domain.cycles.call_cost import CallCost
from autotrading.domain.cycles.cycle_record import AbsentSource, CycleFailure, CycleOutcome, CycleRecord
from autotrading.domain.cycles.cycle_step import CycleStep
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


def test_the_lock_is_released_after_the_cycle(cycles: Cycles) -> None:
    run(cycles)

    with cycles.lock.hold(cycles.id_of("alfa")) as acquired:
        assert acquired


def test_the_absent_sources_are_recorded(cycles: Cycles) -> None:
    cycles.flow("alfa").sources = ("notizie",)
    cycles.sources.failing["notizie"] = FakeTransientError("fonte giù")

    record = run(cycles)

    assert record is not None
    assert record.absent_sources == (AbsentSource("notizie", "fonte giù"),)
    assert cycles.context.composed[cycles.id_of("alfa")].absent == record.absent_sources


def test_the_sources_wait_follows_the_interval(cycles: Cycles) -> None:
    cycles.set_interval("alfa", 2)
    cycles.flow("alfa").sources = ("notizie",)
    cycles.sources.late["notizie"] = 40

    record = run(cycles)

    assert record is not None
    assert record.absent_sources == (AbsentSource("notizie", "nessuna risposta entro 30 secondi"),)


# A source that fails is absent, never a failed cycle (R1.2.5); the record of the cycle closes it.
FAILING_STEPS = [step for step in CycleStep if step not in {CycleStep.COLLECT_SOURCES, CycleStep.RECORD_CYCLE}]


@pytest.mark.parametrize("step", FAILING_STEPS)
def test_a_transient_error_fails_the_cycle_at_its_step(cycles: Cycles, step: CycleStep) -> None:
    flow_id = cycles.id_of("alfa")
    cycles.agent.decisions[flow_id] = ["BTC"]
    cycles.failures.fail_once(flow_id, step, FakeTransientError("timeout"))

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
    cycles.failures.fail_once(cycles.id_of("alfa"), CycleStep.RISK_CHECK, FakeTransientError("timeout"))

    run(cycles)

    [entry] = caplog.records
    assert entry.message == "ciclo registrato"
    assert entry.__dict__["flow_id"] == str(cycles.id_of("alfa"))
    assert entry.__dict__["planned_at"] == at("10:22:00").isoformat()
    assert entry.__dict__["outcome"] == CycleOutcome.FAILED
