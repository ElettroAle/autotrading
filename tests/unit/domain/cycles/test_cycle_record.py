from datetime import UTC, datetime
from uuid import uuid4

from autotrading.domain.cycles.cycle_record import CycleOutcome, CycleRecord, StepDocument
from autotrading.domain.cycles.cycle_step import CycleStep


def test_a_skipped_cycle_keeps_only_its_planned_instant() -> None:
    flow_id, planned_at = uuid4(), datetime(2026, 11, 12, 10, 22, tzinfo=UTC)

    record = CycleRecord.skipped(flow_id, planned_at)

    assert record == CycleRecord(flow_id, planned_at, CycleOutcome.SKIPPED)
    assert (record.started_at, record.steps, record.failure) == (None, (), None)


def test_the_outcomes_speak_italian() -> None:
    assert [outcome.value for outcome in CycleOutcome] == ["concluso", "fallito", "saltato"]


def test_the_steps_are_in_the_order_of_the_cycle() -> None:
    assert [step.value for step in CycleStep] == [
        "lettura dello stato del flusso",
        "raccolta dei dati delle fonti",
        "composizione del contesto",
        "decisione dell'agente",
        "controllo del rischio",
        "esecuzione degli ordini",
        "aggiornamento dello stato del flusso",
        "registrazione del ciclo",
    ]


def test_a_record_gives_the_document_of_a_step() -> None:
    documents = (
        StepDocument(CycleStep.READ_FLOW_STATE, {"versione": 3}),
        StepDocument(CycleStep.AGENT_DECISION, {"risposta": "{}"}),
    )
    record = CycleRecord(uuid4(), datetime(2026, 11, 12, tzinfo=UTC), CycleOutcome.COMPLETED, documents=documents)

    assert record.document(CycleStep.AGENT_DECISION) == {"risposta": "{}"}
    assert record.document(CycleStep.READ_FLOW_STATE) == {"versione": 3}


def test_a_step_the_cycle_never_got_to_has_no_document() -> None:
    record = CycleRecord(uuid4(), datetime(2026, 11, 12, tzinfo=UTC), CycleOutcome.FAILED)

    assert record.document(CycleStep.ORDER_EXECUTION) is None
    assert (record.documents, record.cost) == ((), None)
