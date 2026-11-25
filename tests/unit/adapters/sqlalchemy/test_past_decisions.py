from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import create_engine

from autotrading.adapters.outbound.sqlalchemy.past_decisions import past_decision_of, past_decisions_statement
from autotrading.domain.flows.closed_position import CloseReason
from autotrading.domain.flows.flow_memory import EVERY_DECISION, OPENINGS_AND_CLOSINGS
from autotrading.domain.flows.memory_entry import PastDecision
from autotrading.domain.flows.recorded_decision import DecisionAction, RecordedDecision
from autotrading.domain.flows.statistics_period import TimeWindow
from autotrading.domain.flows.trade_side import TradeSide

PLANNED = datetime(2026, 11, 24, 10, 0, tzinfo=UTC)
# An engine only for its dialect: it never connects.
POSTGRESQL = create_engine("postgresql+psycopg://").dialect


def a_row(action: str, direction: str | None = None, **values: object) -> dict[str, object]:
    row: dict[str, object] = {
        "planned_at": PLANNED,
        "asset": "BTC",
        "action": action,
        "direction": direction,
        "confidence": 70,
        "reasoning": "motivo",
        "motive": None,
        "invalidation": None,
        "price": Decimal(95000),
        "opened_pnl": None,
        "closed_pnl": None,
        "closing_reason": None,
        "position_opened_at": None,
        "position_closed_at": None,
        "opening_executed_at": None,
    }
    return row | values


def test_the_statement_reads_the_decisions_asked_of_the_completed_cycles_of_the_flow_in_the_window() -> None:
    flow_id = uuid4()
    statement = past_decisions_statement(flow_id, TimeWindow(PLANNED - timedelta(days=30), PLANNED), EVERY_DECISION)
    sql = " ".join(str(statement.compile(dialect=POSTGRESQL)).split())
    params = statement.compile().params

    assert "FROM cycle_decisions JOIN cycles ON cycle_decisions.flow_id = cycles.flow_id" in sql
    assert "cycle_decisions.action IN (__[POSTCOMPILE_action_1])" in sql
    assert "cycle_decisions.planned_at >= %(planned_at_1)s" in sql
    assert "cycle_decisions.planned_at < %(planned_at_2)s" in sql
    assert "orders.cycle_planned_at = cycle_decisions.planned_at" in sql
    assert "closed_positions.opening_cycle = cycle_decisions.planned_at" in sql
    assert "closed_positions.closing_cycle = cycle_decisions.planned_at" in sql
    assert "closed_positions.reason" in sql
    assert "closed_positions.opened_at" in sql
    assert "closed_positions.closed_at" in sql
    assert "orders.reduce_only IS false" in sql
    assert "ORDER BY cycle_decisions.planned_at DESC" in sql
    assert flow_id in params.values()
    assert "completed" in params.values()
    assert sorted(params["action_1"]) == ["aggiorna", "apri", "chiudi", "inverti", "mantieni"]


def test_the_statement_reads_only_the_actions_the_memory_remembers() -> None:
    statement = past_decisions_statement(
        uuid4(), TimeWindow(PLANNED - timedelta(days=1), PLANNED), OPENINGS_AND_CLOSINGS
    )

    assert sorted(statement.compile().params["action_1"]) == ["apri", "chiudi", "inverti"]


def test_an_opening_whose_position_closed_has_the_pnl_cause_and_instants_of_that_position() -> None:
    opened_at, closed_at = PLANNED + timedelta(seconds=5), PLANNED + timedelta(minutes=12)
    row = a_row(
        "apri",
        "long",
        motive="rottura",
        invalidation="sotto 90000",
        opened_pnl=Decimal(12),
        closed_pnl=Decimal(-1),
        closing_reason="stop_loss",
        position_opened_at=opened_at,
        position_closed_at=closed_at,
        opening_executed_at=opened_at,
    )

    past = past_decision_of(row)

    decision = RecordedDecision(
        "BTC", DecisionAction.OPEN, TradeSide.LONG, 70, "motivo", motive="rottura", invalidation="sotto 90000"
    )
    assert past == PastDecision(
        PLANNED,
        decision,
        Decimal(95000),
        Decimal(12),
        closed_by=CloseReason.STOP_LOSS,
        opened_at=opened_at,
        closed_at=closed_at,
    )


def test_an_opening_executed_whose_position_did_not_close_is_still_open_since_its_execution() -> None:
    executed_at = PLANNED + timedelta(seconds=3)

    past = past_decision_of(a_row("inverti", opening_executed_at=executed_at))

    assert (past.realized_pnl, past.position_open, past.opened_at, past.closed_by) == (None, True, executed_at, None)


def test_an_opening_never_executed_opened_nothing() -> None:
    past = past_decision_of(a_row("apri", "long", price=None))

    assert (past.price, past.realized_pnl, past.position_open) == (None, None, False)


@pytest.mark.parametrize("action", ["chiudi", "aggiorna"])
def test_any_other_decision_has_the_pnl_of_the_position_it_closed_and_opens_nothing(action: str) -> None:
    row = a_row(
        action,
        opened_pnl=Decimal(3),
        closed_pnl=Decimal(-7),
        closing_reason="agent",
        position_opened_at=PLANNED,
        opening_executed_at=PLANNED,
    )

    past = past_decision_of(row)

    assert (past.realized_pnl, past.position_open) == (Decimal(-7), False)
    assert (past.closed_by, past.opened_at, past.closed_at) == (None, None, None)
