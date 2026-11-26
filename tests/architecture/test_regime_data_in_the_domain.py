"""ADR-dati-di-regime-nella-fonte-indicatori: the extremes, the changes over hours and the series of the closes are
parameters the adapter of the market declares for the indicators only, never of the source nor of the pivots; their
values are named and computed only in the domain of the sources, and the reader of the indicators reads the hourly
candles in the number the choice of the flow asks, behind that choice.
"""

import ast
import re
from pathlib import Path

import pytest

from autotrading.adapters.outbound.hyperliquid.market_data import DECLARATION, INDICATORS_DECLARATION
from autotrading.domain.sources.indicators import INDICATORS
from autotrading.domain.sources.pivots import PIVOTS
from autotrading.domain.sources.regime_data import REGIME_PARAMETERS
from tests.support.architecture import SOURCE_ROOT

ROOT = Path(SOURCE_ROOT)
DOMAIN = ROOT / "domain"
READER = ROOT / "application" / "sources" / "read_indicators.py"
# The prefix of the extremes, the distances as the head of an f-string, the series of the closes written whole.
REGIME_NAME = re.compile(r"estremi\.|^dal_(minimo|massimo)_|chiusura\.serie")
HOURLY_COUNT = "hourly_candles"
CHOICE = "RegimeChoice"


def names_a_regime_value(source: str) -> bool:
    """Whether the module writes the name of a value of the regime data: only who computes the values names them."""
    return any(
        isinstance(node, ast.Constant) and isinstance(node.value, str) and REGIME_NAME.search(node.value) is not None
        for node in ast.walk(ast.parse(source))
    )


def reads_the_hourly_candles_of_the_choice(source: str) -> bool:
    """Whether the module asks the candles in the number the domain declares, behind the choice of the flow."""
    tree = ast.parse(source)
    asks_the_count = any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "candles"
        and any(isinstance(argument, ast.Attribute) and argument.attr == HOURLY_COUNT for argument in node.args)
        for node in ast.walk(tree)
    )
    follows_the_choice = any(isinstance(node, ast.Name) and node.id == CHOICE for node in ast.walk(tree))
    return asks_the_count and follows_the_choice


def test_adr_dati_di_regime_nella_fonte_indicatori_the_parameters_belong_to_the_adapter_for_the_indicators() -> None:
    assert INDICATORS_DECLARATION.parameters == REGIME_PARAMETERS
    assert INDICATORS_DECLARATION.name == DECLARATION.name
    assert not set(REGIME_PARAMETERS) & set(DECLARATION.parameters)
    assert not set(REGIME_PARAMETERS) & {*INDICATORS.parameters, *PIVOTS.parameters}


@pytest.mark.parametrize(
    ("source", "naming"),
    [
        ('values = {"estremi.minimo_24h": low}\n', True),
        ('key = f"dal_minimo_{hours}h"\n', True),
        ('values["breve.chiusura.serie"] = closes\n', True),
        ('values = {"lungo.timeframe": label}\n', False),
        ('key = f"minimo_ordine_{asset}"\n', False),
    ],
)
def test_adr_dati_di_regime_nella_fonte_indicatori_a_regime_value_outside_the_domain_is_found(
    source: str, naming: bool
) -> None:
    assert names_a_regime_value(source) is naming


def test_adr_dati_di_regime_nella_fonte_indicatori_the_values_are_named_only_in_the_domain() -> None:
    outside = [
        str(path.relative_to(ROOT))
        for path in ROOT.rglob("*.py")
        if not path.is_relative_to(DOMAIN) and names_a_regime_value(path.read_text(encoding="utf-8"))
    ]

    assert not outside, f"I dati di regime si nominano e si calcolano nel domain di sources: {outside}"


@pytest.mark.parametrize(
    ("source", "reading"),
    [
        (
            "def read(self):\n"
            "    regime = RegimeChoice.of(settings)\n"
            "    if regime.reads_hourly_candles:\n"
            "        return market.candles(asset, HOURLY, regime.hourly_candles, now)\n",
            True,
        ),
        ("def read(self):\n    return market.candles(asset, HOURLY, choice.hourly_candles, now)\n", False),
        (
            "def read(self):\n"
            "    if RegimeChoice.of(settings).reads_hourly_candles:\n"
            "        return market.candles(asset, HOURLY, 721, now)\n",
            False,
        ),
    ],
)
def test_adr_dati_di_regime_nella_fonte_indicatori_a_reader_that_ignores_the_choice_is_found(
    source: str, reading: bool
) -> None:
    assert reads_the_hourly_candles_of_the_choice(source) is reading


def test_adr_dati_di_regime_nella_fonte_indicatori_the_reader_reads_the_hourly_candles_the_choice_asks() -> None:
    assert reads_the_hourly_candles_of_the_choice(READER.read_text(encoding="utf-8"))
