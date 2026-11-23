import threading
from collections.abc import Iterator
from datetime import timedelta
from decimal import Decimal

import pytest

from autotrading.application.flows.cycle_graph import CompletedCycle, FailedCycle, PlannedCycle, real_seconds
from autotrading.application.flows.ports import FailedModelCall, ReversedExecutions, SourceReading
from autotrading.domain.flows.call_cost import CallCost
from autotrading.domain.flows.cycle_record import AbsentSource, CycleOutcome, CycleRecord, FailedAttempt
from autotrading.domain.flows.cycle_step import CycleStep
from autotrading.domain.flows.recorded_decision import DecisionAction, RecordedDecision
from autotrading.domain.flows.trade_side import TradeSide
from tests.fakes.cycles import FakePermanentError, FakeTransientError
from tests.support.cycles import Cycles, at


@pytest.fixture
def cycles() -> Iterator[Cycles]:
    world = Cycles()
    yield world
    world.release()


def planned(cycles: Cycles, name: str = "alfa") -> PlannedCycle:
    return PlannedCycle(cycles.id_of(name), cycles.flow(name).schedule, at("10:00:00"))


def completed(outcome: CompletedCycle | FailedCycle) -> CycleRecord:
    assert isinstance(outcome, CompletedCycle)
    return outcome.record


def readings_of(record: CycleRecord) -> object:
    document = record.document(CycleStep.COLLECT_SOURCES)
    assert document is not None
    return document["result"]


def test_the_real_wait_lasts_the_seconds_of_the_cycle() -> None:
    assert real_seconds(timedelta(seconds=30)) == 30.0


def test_a_flow_without_sources_goes_straight_to_the_collected_sources(cycles: Cycles) -> None:
    cycles.add_flow("alfa")

    record = completed(cycles.graph().run(planned(cycles), at("10:00:00")))

    assert (record.steps, record.absent_sources, readings_of(record)) == (tuple(CycleStep), (), "[]")


def test_every_active_source_that_answers_gives_its_reading_in_the_order_of_the_flow(cycles: Cycles) -> None:
    cycles.add_flow("alfa", sources=("indicatori", "notizie"))
    flow_id = str(cycles.id_of("alfa"))

    record = completed(cycles.graph().run(planned(cycles), at("10:00:00")))

    assert readings_of(record) == repr(
        [
            SourceReading("indicatori · Hyperliquid", {"source": "indicatori", "flow_id": flow_id}),
            SourceReading("notizie · RSS", {"source": "notizie", "flow_id": flow_id}),
        ]
    )


def test_a_silent_source_is_absent_with_the_wait_in_seconds_and_the_cycle_goes_on(cycles: Cycles) -> None:
    cycles.add_flow("alfa", sources=("indicatori", "notizie"))
    cycles.sources.silent.add("notizie")

    record = completed(cycles.graph().run(planned(cycles), at("10:00:00")))

    wait = int(cycles.flow("alfa").schedule.source_wait.total_seconds())
    assert record.outcome is CycleOutcome.COMPLETED
    assert record.absent_sources == (AbsentSource("notizie", f"nessuna risposta entro {wait} secondi", "RSS"),)


def test_a_source_that_fails_is_absent_with_its_message(cycles: Cycles) -> None:
    cycles.add_flow("alfa", sources=("notizie",))
    cycles.sources.failing["notizie"] = FakeTransientError("limite di richieste superato")

    record = completed(cycles.graph().run(planned(cycles), at("10:00:00")))

    assert record.absent_sources == (AbsentSource("notizie", "limite di richieste superato", "RSS"),)


def test_the_source_nodes_run_together(cycles: Cycles) -> None:
    # Each source answers after two thirds of the wait: one after the other they would not both make it.
    cycles.add_flow("alfa", sources=("indicatori", "notizie"))
    late = cycles.flow("alfa").schedule.source_wait.total_seconds() * 2 / 3
    cycles.sources.late.update({"indicatori": late, "notizie": late})

    record = completed(cycles.graph().run(planned(cycles), at("10:00:00")))

    assert record.absent_sources == ()


def test_a_late_source_is_not_awaited(cycles: Cycles) -> None:
    cycles.add_flow("alfa", sources=("notizie",))
    cycles.sources.silent.add("notizie")
    finished = threading.Event()

    def run() -> None:
        cycles.graph().run(planned(cycles), at("10:00:00"))
        finished.set()

    threading.Thread(target=run, daemon=True).start()

    assert finished.wait(2.0)


def test_a_failed_node_gives_the_steps_done_before_it_and_the_error(cycles: Cycles) -> None:
    cycles.add_flow("alfa")
    error = FakeTransientError("timeout del modello")
    cycles.failures.fail_once(cycles.id_of("alfa"), CycleStep.AGENT_DECISION, error)

    outcome = cycles.graph().run(planned(cycles), at("10:00:00"))

    assert isinstance(outcome, FailedCycle)
    assert outcome.error is error
    assert outcome.record.steps == (CycleStep.READ_FLOW_STATE, CycleStep.COLLECT_SOURCES, CycleStep.COMPOSE_CONTEXT)
    assert outcome.record.failure is not None
    assert outcome.record.failure.step is CycleStep.AGENT_DECISION


def test_an_interrupted_cycle_resumes_from_the_node_that_failed_keeping_what_came_before(cycles: Cycles) -> None:
    cycles.add_flow("alfa")
    flow_id = cycles.id_of("alfa")
    cycles.failures.fail_once(flow_id, CycleStep.AGENT_DECISION, FakeTransientError("timeout del modello"))
    graph = cycles.graph()
    graph.run(planned(cycles), at("10:00:00"))
    contexts_before = len(cycles.agent.contexts)

    record = completed(graph.run(planned(cycles), at("10:05:00")))

    assert record.steps == tuple(CycleStep)
    assert record.started_at == at("10:00:00")
    assert len(cycles.agent.contexts) == contexts_before + 1
    assert [document.step for document in record.documents] == list(CycleStep)[:-1]


def test_a_completed_cycle_gives_the_state_of_the_flow_at_its_end(cycles: Cycles) -> None:
    cycles.add_flow("alfa")

    outcome = cycles.graph().run(planned(cycles), at("10:00:00"))

    assert isinstance(outcome, CompletedCycle)
    assert outcome.state == {"flow": "alfa", "executions": 0}


def test_a_failed_cycle_gives_the_last_state_of_the_flow_it_read(cycles: Cycles) -> None:
    cycles.add_flow("alfa")
    cycles.failures.fail_always(cycles.id_of("alfa"), CycleStep.UPDATE_FLOW_STATE, FakeTransientError("timeout"))

    outcome = cycles.graph().run(planned(cycles), at("10:00:00"))

    assert isinstance(outcome, FailedCycle)
    assert outcome.state == {"flow": "alfa", "positions": []}


def test_a_cycle_failed_recording_itself_gives_the_state_of_the_flow_at_its_end(cycles: Cycles) -> None:
    cycles.add_flow("alfa")
    cycles.records.failing_once = FakeTransientError("database non raggiungibile")

    outcome = cycles.graph().run(planned(cycles), at("10:00:00"))

    assert isinstance(outcome, FailedCycle)
    assert outcome.record.failure is not None
    assert outcome.record.failure.step is CycleStep.RECORD_CYCLE
    assert outcome.state == {"flow": "alfa", "executions": 0}


def test_a_cycle_failed_reading_the_flow_gives_no_state(cycles: Cycles) -> None:
    cycles.add_flow("alfa")
    cycles.failures.fail_always(cycles.id_of("alfa"), CycleStep.READ_FLOW_STATE, FakeTransientError("timeout"))

    outcome = cycles.graph().run(planned(cycles), at("10:00:00"))

    assert isinstance(outcome, FailedCycle)
    assert outcome.state is None


# ADR-costo-della-decisione-fallita-nel-registro-del-ciclo: a cycle failed in the decision records its model call.
def test_a_cycle_failed_in_the_decision_records_the_tokens_and_cost_of_the_call(cycles: Cycles) -> None:
    cycles.add_flow("alfa")
    error = FakeTransientError("risposta del fornitore inattesa")
    cycles.failures.fail_once(cycles.id_of("alfa"), CycleStep.AGENT_DECISION, error)
    cycles.journal.failed = FailedModelCall(CallCost(3000, 4000, Decimal("0.002")), attempts=4)

    outcome = cycles.graph().run(planned(cycles), at("10:00:00"))

    assert isinstance(outcome, FailedCycle)
    assert cycles.journal.failures == [error]
    assert outcome.record.cost == CallCost(3000, 4000, Decimal("0.002"))
    assert not outcome.record.call_without_usage
    assert outcome.record.model_attempts == 4


def test_a_cycle_failed_in_the_decision_without_a_known_usage_records_a_call_without_cost(cycles: Cycles) -> None:
    cycles.add_flow("alfa")
    cycles.failures.fail_once(cycles.id_of("alfa"), CycleStep.AGENT_DECISION, FakeTransientError("scaduto"))
    cycles.journal.failed = FailedModelCall(None, attempts=4)

    outcome = cycles.graph().run(planned(cycles), at("10:00:00"))

    assert isinstance(outcome, FailedCycle)
    assert (outcome.record.cost, outcome.record.call_without_usage) == (None, True)
    assert outcome.record.model_called
    assert outcome.record.model_attempts == 4


# ADR-tentativi-del-modello-registrati-nel-ciclo: attempts that never reached the provider are still attempts.
def test_a_cycle_failed_in_the_decision_with_no_call_out_records_the_attempts_without_a_call(cycles: Cycles) -> None:
    cycles.add_flow("alfa")
    cycles.failures.fail_once(cycles.id_of("alfa"), CycleStep.AGENT_DECISION, FakeTransientError("ConnectError"))
    cycles.journal.failed = FailedModelCall(None, attempts=4, sent=False)

    outcome = cycles.graph().run(planned(cycles), at("10:00:00"))

    assert isinstance(outcome, FailedCycle)
    assert not outcome.record.model_called
    assert outcome.record.model_attempts == 4


def test_a_cycle_failed_in_the_decision_before_any_call_records_no_call(cycles: Cycles) -> None:
    cycles.add_flow("alfa")
    cycles.failures.fail_once(cycles.id_of("alfa"), CycleStep.AGENT_DECISION, FakeTransientError("nessuna chiave"))
    cycles.journal.failed = None

    outcome = cycles.graph().run(planned(cycles), at("10:00:00"))

    assert isinstance(outcome, FailedCycle)
    assert not outcome.record.model_called
    assert outcome.record.model_attempts is None


def test_a_cycle_failed_after_the_decision_keeps_the_cost_of_the_answered_call(cycles: Cycles) -> None:
    cycles.add_flow("alfa")
    cycles.failures.fail_always(cycles.id_of("alfa"), CycleStep.RISK_CHECK, FakeTransientError("timeout"))
    cycles.journal.failed = FailedModelCall(None, attempts=1)
    cycles.journal.attempts = 3

    outcome = cycles.graph().run(planned(cycles), at("10:00:00"))

    assert isinstance(outcome, FailedCycle)
    assert cycles.journal.failures == []
    assert (outcome.record.cost, outcome.record.call_without_usage) == (cycles.journal.cost, False)
    assert outcome.record.model_attempts == 3


# ADR-tentativi-del-modello-registrati-nel-ciclo: a completed cycle records the attempts beside the cost of the call.
def test_a_completed_cycle_records_the_attempts_of_the_model_call(cycles: Cycles) -> None:
    cycles.add_flow("alfa")
    cycles.journal.attempts = 2

    outcome = cycles.graph().run(planned(cycles), at("10:00:00"))

    assert isinstance(outcome, CompletedCycle)
    assert (outcome.record.cost, outcome.record.model_attempts) == (cycles.journal.cost, 2)


# ADR decisioni-del-ciclo-registrate-per-asset: the decide node reads the decisions one by asset through the journal
# and the record of the cycle keeps them, also when the cycle fails after deciding or resumes from a checkpoint.
def opening_of(asset: str) -> RecordedDecision:
    return RecordedDecision(asset, DecisionAction.OPEN, TradeSide.LONG, 70, f"apertura di {asset}")


def test_a_completed_cycle_records_the_decisions_the_journal_reads_one_by_asset(cycles: Cycles) -> None:
    cycles.add_flow("alfa")
    cycles.agent.decisions[cycles.id_of("alfa")] = ["BTC", "ETH"]

    record = completed(cycles.graph().run(planned(cycles), at("10:00:00")))

    assert record.decisions == (opening_of("BTC"), opening_of("ETH"))
    assert cycles.records.records[-1].decisions == record.decisions


def test_a_cycle_failed_after_the_decision_keeps_its_decisions(cycles: Cycles) -> None:
    cycles.add_flow("alfa")
    flow_id = cycles.id_of("alfa")
    cycles.agent.decisions[flow_id] = ["BTC"]
    cycles.failures.fail_always(flow_id, CycleStep.RISK_CHECK, FakeTransientError("timeout"))

    outcome = cycles.graph().run(planned(cycles), at("10:00:00"))

    assert isinstance(outcome, FailedCycle)
    assert outcome.record.decisions == (opening_of("BTC"),)


def test_a_cycle_failed_before_the_decision_has_none(cycles: Cycles) -> None:
    cycles.add_flow("alfa")
    flow_id = cycles.id_of("alfa")
    cycles.agent.decisions[flow_id] = ["BTC"]
    cycles.failures.fail_once(flow_id, CycleStep.AGENT_DECISION, FakeTransientError("timeout del modello"))

    outcome = cycles.graph().run(planned(cycles), at("10:00:00"))

    assert isinstance(outcome, FailedCycle)
    assert outcome.record.decisions == ()


def test_a_resumed_cycle_records_the_decisions_taken_before_it_stopped(cycles: Cycles) -> None:
    cycles.add_flow("alfa")
    flow_id = cycles.id_of("alfa")
    cycles.agent.decisions[flow_id] = ["BTC"]
    # Every attempt of the first run fails; the run that resumes it goes through.
    cycles.failures.fail(flow_id, CycleStep.RISK_CHECK, FakeTransientError("timeout"), times=3)
    graph = cycles.graph()
    graph.run(planned(cycles), at("10:00:00"))
    cycles.agent.decisions[flow_id] = []

    record = completed(graph.run(planned(cycles), at("10:05:00")))

    assert record.decisions == (opening_of("BTC"),)


def order_execution_of(record: CycleRecord) -> object:
    document = record.document(CycleStep.ORDER_EXECUTION)
    assert document is not None
    return document["result"]


# ADR-inversione-in-due-passi-nel-ciclo: the opening of a reversal goes in a second execution, after the first.
def test_a_cycle_with_a_reversal_sends_its_opening_after_the_orders_and_records_both_executions(cycles: Cycles) -> None:
    cycles.add_flow("alfa")
    flow_id = cycles.id_of("alfa")
    cycles.agent.decisions[flow_id] = ["BTC"]
    cycles.risk.reversing = True

    record = completed(cycles.graph().run(planned(cycles), at("10:00:00")))

    assert cycles.reversal.calls == [(flow_id, at("10:00:00"), cycles.flow("alfa").schedule.anchor, ("BTC",))]
    executions = ({"order": "BTC", "filled": True}, {"reopened": "BTC"})
    assert order_execution_of(record) == repr(ReversedExecutions(executions, {"BTC": "riaperta"}))
    assert cycles.flows.updates == [(flow_id, executions)]
    assert record.steps == tuple(CycleStep)
    assert [document.step for document in record.documents] == list(CycleStep)[:-1]


def test_a_cycle_without_reversals_has_no_second_execution(cycles: Cycles) -> None:
    cycles.add_flow("alfa")
    cycles.agent.decisions[cycles.id_of("alfa")] = ["BTC"]

    record = completed(cycles.graph().run(planned(cycles), at("10:00:00")))

    assert cycles.reversal.calls == []
    assert order_execution_of(record) == repr([{"order": "BTC", "filled": True}])


def test_a_failed_reversal_fails_the_cycle_in_the_execution_of_the_orders(cycles: Cycles) -> None:
    cycles.add_flow("alfa")
    cycles.agent.decisions[cycles.id_of("alfa")] = ["BTC"]
    cycles.risk.reversing = True
    error = FakeTransientError("l'exchange non risponde")
    cycles.reversal.failing = error

    outcome = cycles.graph().run(planned(cycles), at("10:00:00"))

    assert isinstance(outcome, FailedCycle)
    assert outcome.error is error
    assert outcome.record.failure is not None
    assert outcome.record.failure.step is CycleStep.ORDER_EXECUTION
    assert CycleStep.ORDER_EXECUTION not in outcome.record.steps


def test_an_interrupted_reversal_resumes_without_sending_the_orders_again(cycles: Cycles) -> None:
    cycles.add_flow("alfa")
    cycles.agent.decisions[cycles.id_of("alfa")] = ["BTC"]
    cycles.risk.reversing = True
    cycles.reversal.failing = FakeTransientError("l'exchange non risponde")
    graph = cycles.graph()
    graph.run(planned(cycles), at("10:00:00"))

    record = completed(graph.run(planned(cycles), at("10:05:00")))

    assert len(cycles.orders.sent) == 1
    assert len(cycles.reversal.calls) == 1
    assert record.steps == tuple(CycleStep)


RETRIED_STEPS = (
    CycleStep.READ_FLOW_STATE,
    CycleStep.COMPOSE_CONTEXT,
    CycleStep.RISK_CHECK,
    CycleStep.UPDATE_FLOW_STATE,
)


# ADR-errori-temporanei-ritentati-in-ogni-passo-del-ciclo: the port of a step is called again in the same cycle.
@pytest.mark.parametrize("step", RETRIED_STEPS)
def test_a_temporary_error_of_a_step_is_retried_and_the_cycle_completes(cycles: Cycles, step: CycleStep) -> None:
    cycles.add_flow("alfa")
    cycles.failures.fail_once(cycles.id_of("alfa"), step, FakeTransientError("exchange non raggiungibile"))

    record = completed(cycles.graph().run(planned(cycles), at("10:00:00")))

    assert record.steps == tuple(CycleStep)
    assert record.failed_attempts == (FailedAttempt(step, 1, "FakeTransientError", "exchange non raggiungibile"),)
    assert cycles.waits.pauses == [5.0]


@pytest.mark.parametrize("step", RETRIED_STEPS)
def test_three_temporary_errors_of_a_step_fail_the_cycle_with_every_attempt(cycles: Cycles, step: CycleStep) -> None:
    cycles.add_flow("alfa")
    error = FakeTransientError("timeout")
    cycles.failures.fail_always(cycles.id_of("alfa"), step, error)

    outcome = cycles.graph().run(planned(cycles), at("10:00:00"))

    assert isinstance(outcome, FailedCycle)
    assert outcome.error is error
    assert outcome.record.failure is not None
    assert outcome.record.failure.step is step
    assert outcome.record.failed_attempts == tuple(
        FailedAttempt(step, attempt, "FakeTransientError", "timeout") for attempt in (1, 2, 3)
    )
    assert cycles.waits.pauses == [5.0, 15.0]


def test_a_permanent_error_of_a_step_is_not_retried(cycles: Cycles) -> None:
    cycles.add_flow("alfa")
    flow_id = cycles.id_of("alfa")
    cycles.failures.fail_once(
        flow_id, CycleStep.READ_FLOW_STATE, FakePermanentError("credenziali del conto non valide")
    )

    outcome = cycles.graph().run(planned(cycles), at("10:00:00"))

    assert isinstance(outcome, FailedCycle)
    assert cycles.flows.reads == [flow_id]
    assert cycles.waits.pauses == []
    assert outcome.record.failed_attempts == (
        FailedAttempt(CycleStep.READ_FLOW_STATE, 1, "FakePermanentError", "credenziali del conto non valide"),
    )


def test_the_decision_of_the_agent_keeps_its_own_attempts_and_is_not_retried_by_the_cycle(cycles: Cycles) -> None:
    cycles.add_flow("alfa")
    flow_id = cycles.id_of("alfa")
    cycles.failures.fail_once(flow_id, CycleStep.AGENT_DECISION, FakeTransientError("timeout del modello"))

    outcome = cycles.graph().run(planned(cycles), at("10:00:00"))

    assert isinstance(outcome, FailedCycle)
    assert cycles.agent.calls == [flow_id]
    assert (outcome.record.failed_attempts, cycles.waits.pauses) == ((), [])


def test_an_order_that_fails_is_never_retried_by_the_cycle(cycles: Cycles) -> None:
    cycles.add_flow("alfa")
    cycles.agent.decisions[cycles.id_of("alfa")] = ["BTC", "ETH"]
    cycles.orders.unanswered.add("ETH")

    outcome = cycles.graph().run(planned(cycles), at("10:00:00"))

    assert isinstance(outcome, FailedCycle)
    assert [order for _flow, _planned, order in cycles.orders.sent] == ["BTC"]
    assert cycles.waits.pauses == []


def test_the_attempts_that_failed_inside_the_orders_go_in_the_record(cycles: Cycles) -> None:
    cycles.add_flow("alfa")
    flow_id = cycles.id_of("alfa")
    retried = FailedAttempt(CycleStep.ORDER_EXECUTION, 1, "OrderExchangeUnavailableError", "BTC: non risponde")
    cycles.agent.decisions[flow_id] = ["BTC"]
    cycles.orders.failed_attempts = (retried,)

    record = completed(cycles.graph().run(planned(cycles), at("10:00:00")))

    assert record.failed_attempts == (retried,)


def test_the_attempts_that_failed_in_the_reversal_go_in_the_record(cycles: Cycles) -> None:
    cycles.add_flow("alfa")
    cycles.agent.decisions[cycles.id_of("alfa")] = ["BTC"]
    cycles.risk.reversing = True
    retried = FailedAttempt(CycleStep.ORDER_EXECUTION, 1, "FlowExchangeUnavailableError", "exchange non raggiungibile")
    cycles.reversal.failed_attempts = (retried,)

    record = completed(cycles.graph().run(planned(cycles), at("10:00:00")))

    assert record.failed_attempts == (retried,)
