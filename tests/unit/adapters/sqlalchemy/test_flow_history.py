import re
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Select, create_engine

from autotrading.adapters.outbound.sqlalchemy.closed_position_repository import row_of as position_row_of
from autotrading.adapters.outbound.sqlalchemy.cycle_repository import row_of as cycle_row_of
from autotrading.adapters.outbound.sqlalchemy.flow_history import (
    closed_positions_statement,
    cycle_entry_of,
    cycles_statement,
    executions_by_order,
    executions_statement,
    order_entry_of,
    orders_statement,
    position_entry_of,
)
from autotrading.domain.flows.cycle_record import CycleOutcome, CycleRecord
from autotrading.domain.flows.history import HistoryCursor, HistoryFilter, HistoryQuery, OrderExecution
from autotrading.domain.flows.statistics_period import StatisticsPeriod
from tests.support.history import ACCOUNT, FLOW, TENANT, a_closed_position

# An engine only for its dialect: it never connects.
POSTGRESQL = create_engine("postgresql+psycopg://").dialect
NOW = datetime(2026, 11, 30, 23, 0, tzinfo=UTC)
ORDER = UUID("00000000-0000-4000-8000-0000000000b1")
EVERYTHING = HistoryQuery.of(HistoryFilter(), NOW, None)
NARROW = HistoryQuery.of(
    HistoryFilter(
        flow_id=FLOW,
        account_id=ACCOUNT,
        period=StatisticsPeriod.named("range", date(2026, 11, 10), date(2026, 11, 20)),
        asset="ETH",
        version=2,
    ),
    NOW,
    HistoryCursor(NOW, ORDER),
)


def sql_of(statement: Select[tuple[object, ...]]) -> str:
    """The statement as PostgreSQL reads it, without the casts the dialect adds to every parameter."""
    compiled = str(statement.compile(dialect=POSTGRESQL))
    return " ".join(re.sub(r"::(TIMESTAMP WITH TIME ZONE|[A-Z]+)", "", compiled).split())


def test_the_cycles_without_filters_are_the_recorded_ones_newest_first_one_more_than_the_page() -> None:
    sql = sql_of(cycles_statement(EVERYTHING))

    assert "cycles.outcome IS NOT NULL" in sql
    assert "ORDER BY cycles.planned_at DESC, cycles.flow_id DESC LIMIT" in sql
    assert "flows.account_id" not in sql
    assert "jsonb" not in sql.lower()
    assert cycles_statement(EVERYTHING).compile().params["param_1"] == 51


def test_the_cycles_read_every_filter_and_the_version_in_force_at_their_start() -> None:
    sql = sql_of(cycles_statement(NARROW))

    assert "cycles.flow_id = %(flow_id_1)s" in sql
    assert "flows.account_id = %(account_id_1)s" in sql
    assert "cycles.planned_at >= %(planned_at_1)s AND cycles.planned_at < %(planned_at_2)s" in sql
    assert "(cycles.planned_at, cycles.flow_id) < (%(param_1)s, %(param_2)s)" in sql
    assert "flow_versions.created_at <= coalesce(cycles.started_at, cycles.planned_at)" in sql
    assert (
        "(SELECT (CAST(flow_versions.configuration AS JSONB))[%(param_4)s] AS anon_1 FROM flow_versions"
        " WHERE flow_versions.flow_id = cycles.flow_id"
        " AND flow_versions.created_at <= coalesce(cycles.started_at, cycles.planned_at)"
        " ORDER BY flow_versions.version DESC LIMIT %(param_5)s) ? %(param_6)s"
    ) in sql


def test_the_closed_positions_read_every_filter_by_their_closing_instant() -> None:
    sql = sql_of(closed_positions_statement(NARROW))

    assert "closed_positions.flow_id = %(flow_id_1)s" in sql
    assert "flows.account_id = %(account_id_1)s" in sql
    assert "closed_positions.asset = %(asset_1)s" in sql
    assert "flow_versions.created_at <= closed_positions.closed_at" in sql
    assert "(closed_positions.closed_at, closed_positions.id) < (%(param_1)s, %(param_2)s)" in sql
    assert "ORDER BY closed_positions.closed_at DESC, closed_positions.id DESC" in sql


def test_the_closed_positions_without_filters_only_page() -> None:
    sql = sql_of(closed_positions_statement(EVERYTHING))

    assert "WHERE true ORDER BY" in sql


def test_the_orders_read_every_filter_by_their_creation_instant() -> None:
    sql = sql_of(orders_statement(NARROW))

    assert "orders.flow_id = %(flow_id_1)s" in sql
    assert "orders.account_id = %(account_id_1)s" in sql
    assert "orders.coin = %(coin_1)s" in sql
    assert "flow_versions.created_at <= orders.created_at" in sql
    assert "LEFT OUTER JOIN flows ON flows.id = orders.flow_id" in sql
    assert "ORDER BY orders.created_at DESC, orders.id DESC" in sql


def test_the_orders_without_filters_only_page() -> None:
    sql = sql_of(orders_statement(EVERYTHING))

    assert "WHERE true ORDER BY" in sql


def test_the_executions_of_the_orders_come_oldest_first() -> None:
    sql = sql_of(executions_statement([ORDER]))

    assert "account_fills.order_id IN" in sql
    assert sql.endswith("ORDER BY account_fills.executed_at, account_fills.id")


def test_a_cycle_row_becomes_an_entry_with_flow_and_version() -> None:
    record = CycleRecord(FLOW, NOW, CycleOutcome.SKIPPED)

    entry = cycle_entry_of(cycle_row_of(record, TENANT) | {"flow_name": "alfa", "version": 3})

    assert (entry.flow_name, entry.version, entry.record) == ("alfa", 3, record)


def test_a_position_row_becomes_an_entry_with_its_identifier_and_flow() -> None:
    position = a_closed_position(NOW)

    entry = position_entry_of(position_row_of(position) | {"id": ORDER, "flow_name": "alfa"})

    assert (entry.position_id, entry.flow_name, entry.position) == (ORDER, "alfa", position)


def test_the_executions_are_grouped_by_their_order() -> None:
    fill = {"order_id": ORDER, "executed_at": NOW, "price": Decimal(91000), "size": Decimal("-0.01"), "fee": Decimal(1)}

    found = executions_by_order([fill, fill | {"price": Decimal(91001)}])

    assert found[ORDER] == [
        OrderExecution(NOW, Decimal(91000), Decimal("-0.01"), Decimal(1)),
        OrderExecution(NOW, Decimal(91001), Decimal("-0.01"), Decimal(1)),
    ]
    assert found[FLOW] == []


def test_an_order_row_reads_status_and_origin_in_the_words_of_the_orders_context() -> None:
    execution = OrderExecution(NOW, Decimal(91000), Decimal("0.01"), Decimal(1))
    row = {
        "id": ORDER,
        "created_at": NOW,
        "account_id": ACCOUNT,
        "account_name": "principale",
        "flow_id": None,
        "flow_name": None,
        "coin": "BTC",
        "direction": "short",
        "reduce_only": True,
        "leverage": 5,
        "requested_size": Decimal("0.01"),
        "status": "PARTIALLY_FILLED",
        "origin": "MANUAL",
    }

    entry = order_entry_of(row, [execution])

    assert (entry.status, entry.origin, entry.closing) == ("eseguito in parte", "comando manuale", True)
    assert (entry.flow_id, entry.flow_name, entry.account_name) == (None, None, "principale")
    assert (entry.asset, entry.direction, entry.leverage) == ("BTC", "short", 5)
    assert entry.executions == (execution,)
