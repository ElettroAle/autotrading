"""ADR-indice-delle-previsioni-in-attesa-e-patrimonio-con-limite-superiore: a migration creates the partial index of
the forecasts awaiting their actual price; every read of the equity of the flows has an upper bound, the instant the
use case takes from the clock, so the database plans on the partitions it needs only.
"""

import ast
import inspect
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import get_type_hints
from uuid import uuid4

from sqlalchemy import Select, select

from autotrading.adapters.outbound.sqlalchemy import equity_snapshot_repository
from autotrading.adapters.outbound.sqlalchemy.tables import equity_snapshots
from autotrading.application.flows.ports import LossReferencesPort
from tests.support.architecture import SOURCE_ROOT, SourceModule, source_modules

MIGRATIONS = Path(__file__).resolve().parents[2] / "migrations" / "versions"
INDEX = "forecasts_awaiting_actual"
EQUITY_READ = "of_flow"
BOUND = "ending_by"
# The window of the curve is bounded by the use case, which the rule on the calls of the port verifies.
WINDOW_QUERY = "of_flow_query"
NOW = datetime(2026, 11, 20, 12, tzinfo=UTC)

UNBOUNDED_CALL = """
def execute(self, command):
    return self._equity.of_flow(command.flow_id, period.window(self._clock()))
"""
BOUNDED_CALL = """
def execute(self, command):
    now = self._clock()
    return self._equity.of_flow(command.flow_id, period.window(now).ending_by(now))
"""


def index_created(name: str) -> str:
    """The source of the migration that creates the index, empty if none does."""
    return next(
        (
            source
            for migration in sorted(MIGRATIONS.glob("*.py"))
            if f'"{name}"' in (source := migration.read_text(encoding="utf-8"))
        ),
        "",
    )


def unbounded_reads(modules: list[SourceModule]) -> list[str]:
    """The calls of the equity read whose window is not ended by the clock."""
    return sorted(
        f"{module.path}:{node.lineno}"
        for module in modules
        for node in ast.walk(module.tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == EQUITY_READ
        if not _is_bounded(node.args[-1] if node.args else None)
    )


def _is_bounded(window: ast.expr | None) -> bool:
    return isinstance(window, ast.Call) and isinstance(window.func, ast.Attribute) and window.func.attr == BOUND


def unbounded_queries(queries: dict[str, Callable[..., Select[tuple[object, ...]]]]) -> list[str]:
    """The queries of the equity without an upper bound on the planned instant."""
    return sorted(name for name, query in queries.items() if "planned_at <" not in str(query(*_arguments_of(query))))


def _arguments_of(query: Callable[..., object]) -> list[object]:
    return [uuid4() if name == "flow_id" else NOW for name in inspect.signature(query).parameters]


def equity_queries() -> dict[str, Callable[..., Select[tuple[object, ...]]]]:
    return {
        name: function
        for name, function in inspect.getmembers(equity_snapshot_repository, inspect.isfunction)
        if name.endswith("_query") and name != WINDOW_QUERY
    }


def unbounded_example(_flow_id: object, since: datetime) -> Select[tuple[object, ...]]:
    return select(equity_snapshots).where(equity_snapshots.c.planned_at >= since)


def test_adr_indice_delle_previsioni_a_migration_creates_the_partial_index_of_the_awaiting_forecasts() -> None:
    migration = index_created(INDEX)

    assert '"forecasts",\n        ["tenant_id", "made_at"]' in migration
    assert 'postgresql_where=sa.text("actual_price IS NULL")' in migration
    assert index_created("an_index_no_migration_creates") == ""


def test_adr_indice_delle_previsioni_every_equity_read_of_the_application_ends_at_the_clock() -> None:
    modules = [module for module in source_modules(SOURCE_ROOT) if module.path.startswith("application/")]

    assert unbounded_reads(modules) == []


def test_adr_indice_delle_previsioni_an_equity_read_without_an_end_is_a_violation() -> None:
    unbounded = SourceModule.parse("application/flows/read_flow_equity.py", UNBOUNDED_CALL)
    bounded = SourceModule.parse("application/flows/read_flow_equity.py", BOUNDED_CALL)

    assert unbounded_reads([unbounded]) == ["application/flows/read_flow_equity.py:3"]
    assert unbounded_reads([bounded]) == []


def test_adr_indice_delle_previsioni_the_references_of_the_losses_end_at_now() -> None:
    hints = get_type_hints(LossReferencesPort.loss_references)

    assert hints["now"] is datetime
    assert equity_queries()
    assert unbounded_queries(equity_queries()) == []


def test_adr_indice_delle_previsioni_a_query_of_the_equity_without_an_upper_bound_is_a_violation() -> None:
    assert unbounded_queries({"peak_query": unbounded_example}) == ["peak_query"]
