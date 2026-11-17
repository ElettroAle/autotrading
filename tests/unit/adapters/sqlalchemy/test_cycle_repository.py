from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import create_engine

from autotrading.adapters.outbound.sqlalchemy.cycle_repository import (
    consecutive_failures_statement,
    plain,
    record_of,
    row_of,
)
from autotrading.application.flows.errors import UnrecordableDocumentError
from autotrading.domain.flows.call_cost import CallCost
from autotrading.domain.flows.cycle_record import (
    AbsentSource,
    CycleFailure,
    CycleOutcome,
    CycleRecord,
    StepDocument,
)
from autotrading.domain.flows.cycle_step import CycleStep
from autotrading.domain.tenancy.tenant_id import TenantId

PLANNED = datetime(2026, 11, 12, 10, 22, tzinfo=UTC)
TENANT = TenantId.new()
# An engine only for its dialect: it never connects.
POSTGRESQL = create_engine("postgresql+psycopg://").dialect
FAILED = CycleRecord(
    flow_id=uuid4(),
    planned_at=PLANNED,
    outcome=CycleOutcome.FAILED,
    started_at=PLANNED,
    delay_seconds=90,
    steps=(CycleStep.READ_FLOW_STATE, CycleStep.COLLECT_SOURCES),
    absent_sources=(AbsentSource("notizie", "nessuna risposta entro 60 secondi"),),
    failure=CycleFailure(CycleStep.COMPOSE_CONTEXT, "FakeTransientError", "timeout"),
    documents=(StepDocument(CycleStep.READ_FLOW_STATE, {"versione": 3, "pesi": {"notizie": 7}}),),
    cost=CallCost(2000, 500, Decimal("0.0031")),
)


def test_a_record_is_saved_with_steps_and_outcome_by_name() -> None:
    row = row_of(FAILED, TENANT)

    assert row == {
        "flow_id": FAILED.flow_id,
        "planned_at": PLANNED,
        "tenant_id": TENANT.value,
        "outcome": "failed",
        "started_at": PLANNED,
        "delay_seconds": 90,
        "steps": ["read_flow_state", "collect_sources"],
        "absent_sources": [{"source": "notizie", "reason": "nessuna risposta entro 60 secondi"}],
        "failure": {"step": "compose_context", "error_type": "FakeTransientError", "message": "timeout"},
        "documents": [{"step": "read_flow_state", "content": {"versione": 3, "pesi": {"notizie": 7}}}],
        "input_tokens": 2000,
        "output_tokens": 500,
        "cost_usd": Decimal("0.0031"),
        "model_called": True,
    }


def test_a_saved_record_reads_back_as_it_was() -> None:
    assert record_of(row_of(FAILED, TENANT)) == FAILED


def test_a_skipped_record_has_no_failure_no_documents_and_no_cost() -> None:
    skipped = CycleRecord.skipped(uuid4(), PLANNED)

    row = row_of(skipped, TENANT)

    assert (row["outcome"], row["failure"], row["documents"], row["steps"]) == ("skipped", None, [], [])
    assert (row["input_tokens"], row["output_tokens"], row["cost_usd"]) == (None, None, None)
    assert not row["model_called"]
    assert record_of(row) == skipped


def test_a_row_taken_before_the_steps_were_saved_reads_with_empty_lists() -> None:
    row = {**row_of(CycleRecord.skipped(uuid4(), PLANNED), TENANT), "steps": None, "absent_sources": None}

    assert record_of(row | {"documents": None}).steps == ()


def test_a_cost_nobody_knows_reads_back_empty_with_its_tokens() -> None:
    record = CycleRecord(uuid4(), PLANNED, CycleOutcome.COMPLETED, cost=CallCost(10, 5, None))

    assert record_of(row_of(record, TENANT)).cost == CallCost(10, 5, None)


def test_a_cost_with_only_part_of_its_tokens_reads_back_as_no_cost() -> None:
    record = CycleRecord(uuid4(), PLANNED, CycleOutcome.COMPLETED, cost=CallCost(10, 5, None))

    assert record_of(row_of(record, TENANT) | {"output_tokens": None}).cost is None


# ADR-costo-della-decisione-fallita-nel-registro-del-ciclo: a call without a known usage is marked as a call.
def test_a_call_without_a_known_usage_is_saved_as_a_call_without_tokens_and_reads_back() -> None:
    record = CycleRecord(uuid4(), PLANNED, CycleOutcome.FAILED, call_without_usage=True)

    row = row_of(record, TENANT)

    assert (row["model_called"], row["input_tokens"], row["output_tokens"], row["cost_usd"]) == (True, None, None, None)
    assert record_of(row) == record


def test_amounts_identifiers_and_instants_become_text_in_a_document() -> None:
    flow_id = uuid4()

    document = plain({"margine": Decimal("50.10"), "flusso": flow_id, "alle": PLANNED, "ordini": [1, "BTC", None]})

    assert document == {
        "margine": "50.10",
        "flusso": str(flow_id),
        "alle": "2026-11-12T10:22:00+00:00",
        "ordini": [1, "BTC", None],
    }


def test_a_value_that_is_not_json_data_never_reaches_the_record() -> None:
    with pytest.raises(UnrecordableDocumentError) as raised:
        plain({"oggetto": object()})

    assert raised.value.status_code == 500
    assert str(raised.value) == "documento del ciclo non registrabile: object"


def test_the_consecutive_failures_count_the_failed_cycles_after_the_last_completed_one_since_the_anchor() -> None:
    flow_id = uuid4()
    statement = consecutive_failures_statement(flow_id)
    sql = " ".join(str(statement.compile(dialect=POSTGRESQL)).split())

    assert sql.startswith("SELECT count(*)")
    assert "FROM cycles" in sql
    assert "cycles.planned_at > (SELECT max(completed.planned_at)" in sql
    assert "cycles.planned_at >= (SELECT flows.cycle_anchor FROM flows" in sql
    assert sorted(value for value in statement.compile().params.values() if isinstance(value, str)) == [
        "completed",
        "failed",
    ]
    assert {value for value in statement.compile().params.values() if not isinstance(value, str)} == {flow_id}
