"""ADR-indicatori-estesi-nel-domain: Fibonacci, Gann and the dominant cycle are parameters of the indicators source,
valid for every adapter, from 0 to 1 and off by default, with the candles they read from 10 to 500 (100 by default);
their formulas live only in the domain of the sources, and the reader of the indicators reads the 4-hour candles in
the number the choice of the flow asks.
"""

import ast
from pathlib import Path

import pytest

from autotrading.adapters.outbound.hyperliquid.market_data import DECLARATION
from autotrading.domain.sources.extended_indicators import EXTENDED_PARAMETERS
from autotrading.domain.sources.indicators import INDICATORS
from tests.support.architecture import SOURCE_ROOT

ROOT = Path(SOURCE_ROOT)
DOMAIN = ROOT / "domain"
READER = ROOT / "application" / "sources" / "read_indicators.py"
FORMULAS = ("fibonacci", "gann", "dominant")
CANDLES_OF_THE_CHOICE = "long_candles"


def defines_a_formula(source: str) -> bool:
    """Whether the module defines a function or a class named after one of the extended indicators."""
    return any(
        isinstance(node, ast.FunctionDef | ast.ClassDef) and any(name in node.name.lower() for name in FORMULAS)
        for node in ast.walk(ast.parse(source))
    )


def reads_the_candles_of_the_choice(source: str) -> bool:
    return any(
        isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == CANDLES_OF_THE_CHOICE
        for node in ast.walk(ast.parse(source))
    )


def test_adr_indicatori_estesi_nel_domain_the_parameters_belong_to_the_source_for_every_adapter() -> None:
    assert [(p.key, p.default, p.minimum, p.maximum) for p in EXTENDED_PARAMETERS] == [
        ("fibonacci", 0, 0, 1),
        ("gann", 0, 0, 1),
        ("ciclo", 0, 0, 1),
        ("candele_estese", 100, 10, 500),
    ]
    assert set(EXTENDED_PARAMETERS) <= set(INDICATORS.parameters)
    assert not set(EXTENDED_PARAMETERS) & set(DECLARATION.parameters)


@pytest.mark.parametrize(
    ("source", "defining"),
    [
        ("def fibonacci_levels(candles):\n    return {}\n", True),
        ("class GannAngles:\n    pass\n", True),
        ("def _dominant_period(closes):\n    return 4\n", True),
        ("def text_of(value):\n    return str(value)\n", False),
    ],
)
def test_adr_indicatori_estesi_nel_domain_a_formula_outside_the_domain_is_found(source: str, defining: bool) -> None:
    assert defines_a_formula(source) is defining


def test_adr_indicatori_estesi_nel_domain_the_formulas_live_only_in_the_domain() -> None:
    outside = [
        str(path.relative_to(ROOT))
        for path in ROOT.rglob("*.py")
        if not path.is_relative_to(DOMAIN) and defines_a_formula(path.read_text(encoding="utf-8"))
    ]

    assert not outside, f"Le formule degli indicatori estesi stanno nel domain di sources: {outside}"


@pytest.mark.parametrize(
    ("source", "reading"),
    [
        (
            "def execute(self):\n    return market.candles(asset, LONG, extended.long_candles(asked), now)\n",
            True,
        ),
        ("def execute(self):\n    return market.candles(asset, LONG, length + WARM_UP, now)\n", False),
    ],
)
def test_adr_indicatori_estesi_nel_domain_a_reader_that_ignores_the_choice_is_found(source: str, reading: bool) -> None:
    assert reads_the_candles_of_the_choice(source) is reading


def test_adr_indicatori_estesi_nel_domain_the_reader_reads_the_candles_the_choice_asks() -> None:
    assert reads_the_candles_of_the_choice(READER.read_text(encoding="utf-8"))
