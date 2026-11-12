from datetime import UTC, datetime
from uuid import uuid4

from autotrading.domain.cycles.cycle_record import CycleOutcome, CycleRecord
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
