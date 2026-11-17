from datetime import UTC, datetime
from uuid import uuid4

import pytest

from autotrading.domain.flows.cycle_record import CycleOutcome, CycleRecord, StepDocument
from autotrading.domain.flows.cycle_step import CycleStep
from autotrading.domain.flows.errors import UnknownCycleOutcomeError
from autotrading.domain.flows.recorded_decision import DecisionAction, RecordedDecision
from autotrading.domain.flows.trade_side import TradeSide


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


def test_an_outcome_is_named_by_its_italian_word() -> None:
    assert CycleOutcome.named("fallito") is CycleOutcome.FAILED


def test_an_outcome_nobody_records_is_refused_with_the_outcomes_to_choose_from() -> None:
    with pytest.raises(
        UnknownCycleOutcomeError, match="esito non valido: scegliere tra concluso, fallito, saltato"
    ) as raised:
        CycleOutcome.named("failed")

    assert raised.value.outcomes == ("concluso", "fallito", "saltato")


def test_a_cycle_keeps_the_decisions_the_agent_took_in_it() -> None:
    decision = RecordedDecision("BTC", DecisionAction.OPEN, TradeSide.LONG, 72, "trend")
    record = CycleRecord(
        uuid4(), datetime(2026, 11, 16, 10, 0, tzinfo=UTC), CycleOutcome.COMPLETED, decisions=(decision,)
    )

    assert record.decisions == (decision,)


def test_a_cycle_that_never_got_to_the_agent_has_no_decision() -> None:
    assert CycleRecord.skipped(uuid4(), datetime(2026, 11, 16, 10, 0, tzinfo=UTC)).decisions == ()
