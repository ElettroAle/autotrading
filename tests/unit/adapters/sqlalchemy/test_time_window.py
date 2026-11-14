from datetime import UTC, datetime

from sqlalchemy import ColumnElement, create_engine

from autotrading.adapters.outbound.sqlalchemy.tables import closed_positions
from autotrading.adapters.outbound.sqlalchemy.time_window import within
from autotrading.domain.flows.statistics_period import TimeWindow

# The engine never connects: it only gives the dialect of PostgreSQL to the compiler.
ENGINE = create_engine("postgresql+psycopg://nobody@unreachable.invalid/none")
START = datetime(2026, 11, 1, tzinfo=UTC)
END = datetime(2026, 11, 4, tzinfo=UTC)


def sql(condition: ColumnElement[bool]) -> str:
    return str(condition.compile(ENGINE, compile_kwargs={"literal_binds": True}))


def test_a_window_without_bounds_keeps_every_row() -> None:
    assert sql(within(closed_positions.c.closed_at, TimeWindow())) == "true"


def test_a_window_keeps_the_rows_from_its_start_included() -> None:
    condition = sql(within(closed_positions.c.closed_at, TimeWindow(since=START)))

    assert condition == "closed_positions.closed_at >= '2026-11-01 00:00:00+00:00'"


def test_a_window_keeps_the_rows_up_to_its_end_excluded() -> None:
    condition = sql(within(closed_positions.c.closed_at, TimeWindow(since=START, until=END)))

    assert condition == (
        "closed_positions.closed_at >= '2026-11-01 00:00:00+00:00' "
        "AND closed_positions.closed_at < '2026-11-04 00:00:00+00:00'"
    )


def test_a_window_with_only_an_end_keeps_the_rows_before_it() -> None:
    condition = sql(within(closed_positions.c.closed_at, TimeWindow(until=END)))

    assert condition == "closed_positions.closed_at < '2026-11-04 00:00:00+00:00'"
