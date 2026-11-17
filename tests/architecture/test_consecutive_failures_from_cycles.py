"""ADR-pausa-dopo-cicli-falliti-consecutivi: the failed cycles in a row are counted on the recorded cycles, never kept
as a counter beside the flow, and only the adapter of the recorded cycles counts them.
"""

import ast
import inspect
import re

from sqlalchemy import Column, Integer, MetaData, Table

from autotrading.adapters.outbound.sqlalchemy.cycle_repository import SqlAlchemyCycleRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.tables import cycles, metadata
from autotrading.application.flows.ports import ConsecutiveFailuresPort
from tests.support.architecture import SOURCE_ROOT, SourceModule, source_modules

# A column that would keep the failures of a flow apart from the cycles that record them.
COUNTER = re.compile(r"fail|consecutive|streak", re.IGNORECASE)
CYCLES_ADAPTER = "adapters/outbound/sqlalchemy/cycle_repository.py"


def counter_columns(tables: MetaData) -> list[str]:
    """The columns, out of the recorded cycles, that would count the failures of a flow."""
    return sorted(
        f"{table.name}.{column.name}"
        for table in tables.tables.values()
        if table.name != cycles.name
        for column in table.columns
        if COUNTER.search(column.name)
    )


def port_methods() -> set[str]:
    return {
        name for name, _ in inspect.getmembers(ConsecutiveFailuresPort, inspect.isfunction) if not name.startswith("_")
    }


def counting_modules(modules: list[SourceModule], methods: set[str]) -> list[str]:
    """The adapter modules that define a method of the port: only the adapter of the recorded cycles may."""
    return sorted(
        module.path
        for module in modules
        if module.path.startswith("adapters/")
        for node in ast.walk(module.tree)
        if isinstance(node, ast.FunctionDef) and node.name in methods
    )


def test_adr_consecutive_failures_no_table_keeps_a_counter_beside_the_cycles() -> None:
    assert counter_columns(metadata) == []


def test_adr_consecutive_failures_a_counter_on_the_flows_is_a_violation() -> None:
    tables = MetaData()
    Table("flows", tables, Column("consecutive_failures", Integer))
    Table(cycles.name, tables, Column("failure", Integer))

    assert counter_columns(tables) == ["flows.consecutive_failures"]


def test_adr_consecutive_failures_the_adapter_of_the_recorded_cycles_counts_them() -> None:
    methods = port_methods()

    assert methods
    assert all(callable(getattr(SqlAlchemyCycleRepositoryAdapter, name, None)) for name in methods)
    assert counting_modules(source_modules(SOURCE_ROOT), methods) == [CYCLES_ADAPTER]


def test_adr_consecutive_failures_another_adapter_counting_them_is_a_violation() -> None:
    methods = port_methods()
    elsewhere = SourceModule.parse(
        "adapters/outbound/sqlalchemy/flow_repository.py",
        "class X:\n    def consecutive_failures(self, flow_id): ...\n",
    )

    assert counting_modules([elsewhere], methods) == ["adapters/outbound/sqlalchemy/flow_repository.py"]
