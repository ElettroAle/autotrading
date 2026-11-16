"""ADR-perdita-massima-sui-valori-di-equity-registrati: the references of the maximum losses come from the recorded
equities, never from references kept beside the flow, and only the adapter of the recorded equities reads them; the
suspension blocks the openings inside the risk check, never in a separate check.
"""

import ast
import inspect
import re

from sqlalchemy import Column, MetaData, Numeric, Table

from autotrading.adapters.outbound.sqlalchemy.equity_snapshot_repository import (
    SqlAlchemyEquitySnapshotRepositoryAdapter,
)
from autotrading.adapters.outbound.sqlalchemy.tables import metadata
from autotrading.application.flows.ports import LossReferencesPort
from tests.support.architecture import SOURCE_ROOT, SourceModule, source_modules

# A column of the flows that would keep a reference of the losses apart from the equities the cycles record.
KEPT_REFERENCE = re.compile(r"peak|reference|equity", re.IGNORECASE)
FLOWS = "flows"
EQUITY_ADAPTER = "adapters/outbound/sqlalchemy/equity_snapshot_repository.py"
RISK_CHECK = "domain/flows/risk_check.py"
SUSPENSION = "openings_suspended"
# The notice of the suspension shares the name: it tells the user, it blocks nothing.
NOTICE = "Notification"


def kept_references(tables: MetaData) -> list[str]:
    """The columns of the flows that would keep a reference of the losses beside the flow."""
    return sorted(
        f"{FLOWS}.{column.name}" for column in tables.tables[FLOWS].columns if KEPT_REFERENCE.search(column.name)
    )


def port_methods() -> set[str]:
    return {name for name, _ in inspect.getmembers(LossReferencesPort, inspect.isfunction) if not name.startswith("_")}


def reference_readers(modules: list[SourceModule], methods: set[str]) -> list[str]:
    """The adapter modules that define a method of the port: only the adapter of the recorded equities may."""
    return sorted(
        module.path
        for module in modules
        if module.path.startswith("adapters/")
        for node in ast.walk(module.tree)
        if isinstance(node, ast.FunctionDef) and node.name in methods
    )


def suspension_readers(modules: list[SourceModule]) -> list[str]:
    """The modules that read whether the openings are suspended to act on it: only the risk check may."""
    return sorted(
        {
            module.path
            for module in modules
            for node in ast.walk(module.tree)
            if isinstance(node, ast.Attribute) and node.attr == SUSPENSION and not _is_notice(node.value)
        }
    )


def _is_notice(owner: ast.expr) -> bool:
    return isinstance(owner, ast.Name) and owner.id == NOTICE


def test_adr_maximum_loss_the_flows_keep_no_reference_beside_the_recorded_equities() -> None:
    assert kept_references(metadata) == []


def test_adr_maximum_loss_a_peak_kept_on_the_flows_is_a_violation() -> None:
    tables = MetaData()
    Table(FLOWS, tables, Column("peak_equity", Numeric), Column("openings_suspended_at", Numeric))

    assert kept_references(tables) == ["flows.peak_equity"]


def test_adr_maximum_loss_the_adapter_of_the_recorded_equities_reads_the_references() -> None:
    methods = port_methods()

    assert methods
    assert all(callable(getattr(SqlAlchemyEquitySnapshotRepositoryAdapter, name, None)) for name in methods)
    assert reference_readers(source_modules(SOURCE_ROOT), methods) == [EQUITY_ADAPTER]


def test_adr_maximum_loss_another_adapter_reading_the_references_is_a_violation() -> None:
    elsewhere = SourceModule.parse(
        "adapters/outbound/sqlalchemy/flow_repository.py",
        "class X:\n    def loss_references(self, flow_id, day_start, peak_since): ...\n",
    )

    assert reference_readers([elsewhere], port_methods()) == ["adapters/outbound/sqlalchemy/flow_repository.py"]


def test_adr_maximum_loss_only_the_risk_check_blocks_the_suspended_openings() -> None:
    assert suspension_readers(source_modules(SOURCE_ROOT)) == [RISK_CHECK]


def test_adr_maximum_loss_a_separate_check_of_the_suspension_is_a_violation() -> None:
    separate = SourceModule.parse(
        "application/flows/block_suspended_openings.py",
        "def blocked(state, intents):\n    return [] if state.openings_suspended else intents\n",
    )

    assert suspension_readers([separate]) == ["application/flows/block_suspended_openings.py"]
