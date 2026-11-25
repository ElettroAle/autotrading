from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import ClauseElement, create_engine

from autotrading.adapters.outbound.sqlalchemy.cycle_repository import (
    consecutive_failures_statement,
    dated_decisions_of,
    decided_cycle_of,
    decision_count_statement,
    decision_rows_of,
    decisions_statement,
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
    FailedAttempt,
    StepDocument,
)
from autotrading.domain.flows.cycle_step import CycleStep
from autotrading.domain.flows.cycle_trigger import CycleTrigger
from autotrading.domain.flows.decision_filter import DecisionFilter
from autotrading.domain.flows.memory_entry import AssetMemory, MemoryEntry, MemoryOutcome
from autotrading.domain.flows.recorded_decision import DatedDecision, DecidedCycle, DecisionAction, RecordedDecision
from autotrading.domain.flows.statistics_period import TimeWindow
from autotrading.domain.flows.trade_side import TradeSide
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
    absent_sources=(AbsentSource("notizie", "nessuna risposta entro 60 secondi", "RSS"),),
    failure=CycleFailure(CycleStep.COMPOSE_CONTEXT, "FakeTransientError", "timeout"),
    documents=(StepDocument(CycleStep.READ_FLOW_STATE, {"versione": 3, "pesi": {"notizie": 7}}),),
    cost=CallCost(2000, 500, Decimal("0.0031")),
    model_attempts=4,
    failed_attempts=(
        FailedAttempt(CycleStep.READ_FLOW_STATE, 1, "FlowExchangeUnavailableError", "exchange non raggiungibile"),
        FailedAttempt(CycleStep.COMPOSE_CONTEXT, 1, "FakeTransientError", "timeout"),
    ),
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
        "absent_sources": [{"source": "notizie", "reason": "nessuna risposta entro 60 secondi", "adapter": "RSS"}],
        "failure": {"step": "compose_context", "error_type": "FakeTransientError", "message": "timeout"},
        "documents": [{"step": "read_flow_state", "content": {"versione": 3, "pesi": {"notizie": 7}}}],
        "input_tokens": 2000,
        "output_tokens": 500,
        "cost_usd": Decimal("0.0031"),
        "model_called": True,
        "model_attempts": 4,
        "trigger": "scheduled",
        "failed_attempts": [
            {
                "step": "read_flow_state",
                "attempt": 1,
                "error_type": "FlowExchangeUnavailableError",
                "message": "exchange non raggiungibile",
            },
            {"step": "compose_context", "attempt": 1, "error_type": "FakeTransientError", "message": "timeout"},
        ],
        "memory": None,
    }


def test_a_saved_record_reads_back_as_it_was() -> None:
    assert record_of(row_of(FAILED, TENANT)) == FAILED


def test_an_absent_source_recorded_before_the_adapters_reads_back_without_adapter() -> None:
    row = row_of(FAILED, TENANT) | {"absent_sources": [{"source": "notizie", "reason": "fonte giù"}]}

    assert record_of(row).absent_sources == (AbsentSource("notizie", "fonte giù"),)


def test_a_skipped_record_has_no_failure_no_documents_and_no_cost() -> None:
    skipped = CycleRecord.skipped(uuid4(), PLANNED)

    row = row_of(skipped, TENANT)

    assert (row["outcome"], row["failure"], row["documents"], row["steps"]) == ("skipped", None, [], [])
    assert (row["input_tokens"], row["output_tokens"], row["cost_usd"]) == (None, None, None)
    assert not row["model_called"]
    assert row["model_attempts"] is None
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


OPENING = RecordedDecision(
    "BTC", DecisionAction.OPEN, TradeSide.LONG, 72, "trend rialzista", motive="rottura", invalidation="sotto 90000"
)
HOLDING = RecordedDecision("ETH", DecisionAction.HOLD, None, None, "attesa")


def test_the_decisions_of_a_record_are_saved_one_row_each_in_their_order() -> None:
    record = CycleRecord(uuid4(), PLANNED, CycleOutcome.COMPLETED, decisions=(OPENING, HOLDING))

    rows = decision_rows_of(record, TENANT)

    common = {"tenant_id": TENANT.value, "flow_id": record.flow_id, "planned_at": PLANNED}
    assert rows == [
        common
        | {
            "position": 0,
            "asset": "BTC",
            "action": "apri",
            "direction": "long",
            "confidence": 72,
            "reasoning": "trend rialzista",
            "motive": "rottura",
            "invalidation": "sotto 90000",
        },
        common
        | {
            "position": 1,
            "asset": "ETH",
            "action": "mantieni",
            "direction": None,
            "confidence": None,
            "reasoning": "attesa",
            "motive": None,
            "invalidation": None,
        },
    ]


def test_a_record_without_decisions_saves_no_row() -> None:
    assert decision_rows_of(CycleRecord.skipped(uuid4(), PLANNED), TENANT) == []


def test_the_saved_decisions_of_a_cycle_read_back_as_they_were() -> None:
    record = CycleRecord(uuid4(), PLANNED, CycleOutcome.COMPLETED, decisions=(OPENING, HOLDING))

    assert decided_cycle_of(decision_rows_of(record, TENANT)) == DecidedCycle(PLANNED, (OPENING, HOLDING))


def test_no_saved_decision_reads_as_no_decided_cycle() -> None:
    assert decided_cycle_of([]) is None


def test_a_cycle_asked_for_now_is_saved_and_read_back_as_asked() -> None:
    asked = replace(FAILED, trigger=CycleTrigger.ON_DEMAND)

    row = row_of(asked, TENANT)

    assert row["trigger"] == "on_demand"
    assert record_of(row) == asked


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


def sql_of(statement: ClauseElement) -> str:
    return " ".join(str(statement.compile(dialect=POSTGRESQL)).split())


# ADR storico-delle-decisioni-nell-api: the history reads the table of the decisions, joined to the completed cycles.
def test_the_history_reads_the_decisions_of_the_completed_cycles_newest_first_then_by_asset() -> None:
    flow_id = uuid4()
    statement = decisions_statement(flow_id, DecisionFilter(), TimeWindow())
    sql = sql_of(statement)

    assert sql.startswith("SELECT cycle_decisions.flow_id, cycle_decisions.planned_at")
    assert "FROM cycle_decisions JOIN cycles ON cycle_decisions.flow_id = cycles.flow_id" in sql
    assert "AND cycle_decisions.planned_at = cycles.planned_at" in sql
    assert "cycles.outcome = %(outcome_1)s" in sql
    assert sql.endswith("ORDER BY cycle_decisions.planned_at DESC, cycle_decisions.asset, cycle_decisions.position")
    assert statement.compile().params["outcome_1"] == "completed"


def test_the_history_narrows_by_asset_action_direction_and_window() -> None:
    since = PLANNED - timedelta(days=7)
    criteria = DecisionFilter("BTC", DecisionAction.OPEN, TradeSide.LONG)
    statement = decisions_statement(uuid4(), criteria, TimeWindow(since, PLANNED))
    sql = sql_of(statement)
    params = statement.compile().params

    assert "cycle_decisions.asset = %(asset_1)s" in sql
    assert "cycle_decisions.action = %(action_1)s" in sql
    assert "cycle_decisions.direction = %(direction_1)s" in sql
    assert "cycle_decisions.planned_at >= %(planned_at_1)s" in sql
    assert "cycle_decisions.planned_at < %(planned_at_2)s" in sql
    assert (params["asset_1"], params["action_1"], params["direction_1"]) == ("BTC", "apri", "long")
    assert (params["planned_at_1"], params["planned_at_2"]) == (since, PLANNED)


def test_a_filter_without_values_does_not_narrow_the_history() -> None:
    sql = sql_of(decisions_statement(uuid4(), DecisionFilter(), TimeWindow()))

    assert "cycle_decisions.asset =" not in sql
    assert "cycle_decisions.action =" not in sql
    assert "cycle_decisions.direction =" not in sql


def test_the_count_of_the_history_counts_the_same_decisions() -> None:
    criteria = DecisionFilter(asset="ETH")
    sql = sql_of(decision_count_statement(uuid4(), criteria, TimeWindow()))

    assert sql.startswith("SELECT count(*) AS count_1 FROM cycle_decisions JOIN cycles")
    assert "cycles.outcome = %(outcome_1)s" in sql
    assert "cycle_decisions.asset = %(asset_1)s" in sql
    assert "ORDER BY" not in sql


def test_the_saved_decisions_read_back_with_the_instant_of_their_cycle() -> None:
    record = CycleRecord(uuid4(), PLANNED, CycleOutcome.COMPLETED, decisions=(OPENING, HOLDING))

    assert dated_decisions_of(decision_rows_of(record, TENANT)) == [
        DatedDecision(PLANNED, OPENING),
        DatedDecision(PLANNED, HOLDING),
    ]


def test_a_cycle_recorded_before_the_attempts_were_kept_reads_back_without_failed_attempts() -> None:
    row = row_of(FAILED, TENANT) | {"failed_attempts": None}

    assert record_of(row).failed_attempts == ()


REMEMBERED = (
    AssetMemory(
        "BTC",
        (
            MemoryEntry(
                PLANNED - timedelta(hours=1),
                "BTC",
                DecisionAction.OPEN,
                TradeSide.LONG,
                Decimal("95000.5"),
                "rottura",
                "sotto 90000",
                MemoryOutcome(Decimal("-2.25"), realized=False, course="aperta da 1 ora"),
            ),
            MemoryEntry(PLANNED - timedelta(hours=3), "BTC", DecisionAction.UPDATE, None, None, "stop", None, None),
        ),
    ),
    AssetMemory("ETH", ()),
)


def test_the_memory_the_agent_received_is_saved_as_json_with_amounts_as_text() -> None:
    row = row_of(replace(FAILED, memory=REMEMBERED), TENANT)

    assert row["memory"] == [
        {
            "asset": "BTC",
            "entries": [
                {
                    "planned_at": "2026-11-12T09:22:00+00:00",
                    "action": "apri",
                    "direction": "long",
                    "price": "95000.5",
                    "motive": "rottura",
                    "invalidation": "sotto 90000",
                    "outcome": {"pnl": "-2.25", "realized": False, "course": "aperta da 1 ora"},
                },
                {
                    "planned_at": "2026-11-12T07:22:00+00:00",
                    "action": "aggiorna",
                    "direction": None,
                    "price": None,
                    "motive": "stop",
                    "invalidation": None,
                    "outcome": None,
                },
            ],
        },
        {"asset": "ETH", "entries": []},
    ]


def test_the_saved_memory_reads_back_as_it_was() -> None:
    record = replace(FAILED, memory=REMEMBERED)

    assert record_of(row_of(record, TENANT)) == record


def test_a_memory_saved_before_the_motive_reads_its_reasoning_as_the_motive_without_invalidation_nor_course() -> None:
    entry = {
        "planned_at": "2026-11-12T09:22:00+00:00",
        "action": "apri",
        "direction": "long",
        "price": "95000.5",
        "reasoning": "rottura",
        "outcome": {"pnl": "-2.25", "realized": False},
    }
    row = row_of(FAILED, TENANT) | {"memory": [{"asset": "BTC", "entries": [entry]}]}

    [remembered] = record_of(row).memory or ()

    assert remembered.entries == (
        MemoryEntry(
            PLANNED - timedelta(hours=1),
            "BTC",
            DecisionAction.OPEN,
            TradeSide.LONG,
            Decimal("95000.5"),
            "rottura",
            None,
            MemoryOutcome(Decimal("-2.25"), realized=False),
        ),
    )
