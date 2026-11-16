"""ADR-rendimento-composto-tra-le-variazioni-di-capitale: the return of a flow has one computation, `FlowReturn`, which
chains the periods between the changes of the capital. No other module measures a return against the capital
allocated: a division by it would move the return whenever the user changes the capital.
"""

import ast

import pytest

from tests.support.architecture import SOURCE_ROOT, SourceModule, source_modules

CANONICAL = "domain/flows/flow_return.py"
CANONICAL_NAME = "FlowReturn"
CAPITAL_NAMES = frozenset({"allocated_capital", "assigned_capital"})

# The return as FlowState computed it before the ADR: against the capital allocated now.
AGAINST_THE_CAPITAL = """
class FlowState:
    @property
    def return_percent(self):
        return (self.total_value - self.allocated_capital) / self.allocated_capital * HUNDRED
"""
AGAINST_THE_CAPITAL_IN_A_FUNCTION = """
def gain_percent(flow, value):
    capital = flow.configuration.assigned_capital
    return (value - capital) / (flow.configuration.assigned_capital) * 100
"""
THROUGH_THE_CANONICAL = """
class CycleFunds:
    @property
    def return_percent(self):
        return FlowReturn.of(self.attributed).percent
"""


def _names_in(node: ast.AST) -> set[str]:
    names: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Attribute):
            names.add(child.attr)
        if isinstance(child, ast.Name):
            names.add(child.id)
    return names


def returns_against_the_capital(module: SourceModule) -> list[str]:
    """Every division of the module by an expression of the capital allocated, as path and line."""
    return [
        f"src/autotrading/{module.path}:{node.lineno}"
        for node in ast.walk(module.tree)
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div) and _names_in(node.right) & CAPITAL_NAMES
    ]


def test_adr_rendimento_composto_no_module_measures_a_return_against_the_capital_allocated() -> None:
    found = [location for module in source_modules(SOURCE_ROOT) for location in returns_against_the_capital(module)]

    assert found == [], f"il rendimento si calcola solo con {CANONICAL_NAME} ({CANONICAL}): {found}"


def test_adr_rendimento_composto_the_canonical_computation_exists() -> None:
    [module] = [module for module in source_modules(SOURCE_ROOT) if module.path == CANONICAL]

    assert CANONICAL_NAME in {node.name for node in ast.walk(module.tree) if isinstance(node, ast.ClassDef)}


@pytest.mark.parametrize("text", [AGAINST_THE_CAPITAL, AGAINST_THE_CAPITAL_IN_A_FUNCTION])
def test_adr_rendimento_composto_a_return_against_the_capital_is_found(text: str) -> None:
    module = SourceModule.parse("domain/flows/flow_state.py", text)

    assert len(returns_against_the_capital(module)) == 1


def test_adr_rendimento_composto_a_return_read_from_the_canonical_computation_is_not_found() -> None:
    module = SourceModule.parse("domain/flows/cycle_funds.py", THROUGH_THE_CANONICAL)

    assert returns_against_the_capital(module) == []
