import threading
from collections.abc import Iterator
from datetime import timedelta

import pytest

from autotrading.application.flows.cycle_graph import FailedCycle, PlannedCycle, real_seconds
from autotrading.application.flows.ports import SourceReading
from autotrading.domain.flows.cycle_record import AbsentSource, CycleOutcome, CycleRecord
from autotrading.domain.flows.cycle_step import CycleStep
from tests.fakes.cycles import FakeTransientError
from tests.support.cycles import Cycles, at


@pytest.fixture
def cycles() -> Iterator[Cycles]:
    world = Cycles()
    yield world
    world.release()


def planned(cycles: Cycles, name: str = "alfa") -> PlannedCycle:
    return PlannedCycle(cycles.id_of(name), cycles.flow(name).schedule, at("10:00:00"))


def completed(outcome: CycleRecord | FailedCycle) -> CycleRecord:
    assert isinstance(outcome, CycleRecord)
    return outcome


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
            SourceReading("indicatori", {"source": "indicatori", "flow_id": flow_id}),
            SourceReading("notizie", {"source": "notizie", "flow_id": flow_id}),
        ]
    )


def test_a_silent_source_is_absent_with_the_wait_in_seconds_and_the_cycle_goes_on(cycles: Cycles) -> None:
    cycles.add_flow("alfa", sources=("indicatori", "notizie"))
    cycles.sources.silent.add("notizie")

    record = completed(cycles.graph().run(planned(cycles), at("10:00:00")))

    wait = int(cycles.flow("alfa").schedule.source_wait.total_seconds())
    assert record.outcome is CycleOutcome.COMPLETED
    assert record.absent_sources == (AbsentSource("notizie", f"nessuna risposta entro {wait} secondi"),)


def test_a_source_that_fails_is_absent_with_its_message(cycles: Cycles) -> None:
    cycles.add_flow("alfa", sources=("notizie",))
    cycles.sources.failing["notizie"] = FakeTransientError("limite di richieste superato")

    record = completed(cycles.graph().run(planned(cycles), at("10:00:00")))

    assert record.absent_sources == (AbsentSource("notizie", "limite di richieste superato"),)


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
