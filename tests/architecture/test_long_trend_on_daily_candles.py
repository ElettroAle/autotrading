"""ADR-tendenza-lunga-sulle-candele-giornaliere: the trend over several days is a parameter of the indicators source,
valid for every adapter, from 0 to 1 and off by default; its values are computed only in the domain of the sources, on
the daily candles the reader of the indicators asks the same market for, in the number the domain declares and only
when the choice of the flow switches the trend on.
"""

import ast
import re
from pathlib import Path

import pytest

from autotrading.adapters.outbound.hyperliquid.market_data import DECLARATION
from autotrading.domain.sources.indicators import INDICATORS
from autotrading.domain.sources.long_trend import LONG_TREND
from tests.support.architecture import SOURCE_ROOT

ROOT = Path(SOURCE_ROOT)
DOMAIN = ROOT / "domain"
READER = ROOT / "application" / "sources" / "read_indicators.py"
# The prefix of the values, a change in days alone or as the head of an f-string, the channel, the last close.
TREND_NAME = re.compile(r"tendenza\.|^variazione_(\d+g)?$|_20g|ultima_chiusura")
DAILY_COUNT = "DAILY_CANDLES"
CHOICE = "LongTrendChoice"


def names_a_trend_value(source: str) -> bool:
    """Whether the module writes the name of a value of the trend: only who computes the values names them."""
    return any(
        isinstance(node, ast.Constant) and isinstance(node.value, str) and TREND_NAME.search(node.value) is not None
        for node in ast.walk(ast.parse(source))
    )


def reads_the_daily_candles_of_the_choice(source: str) -> bool:
    """Whether the module asks the candles in the number the domain declares, behind the choice of the flow."""
    tree = ast.parse(source)
    asks_the_count = any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "candles"
        and any(isinstance(argument, ast.Name) and argument.id == DAILY_COUNT for argument in node.args)
        for node in ast.walk(tree)
    )
    follows_the_choice = any(isinstance(node, ast.Name) and node.id == CHOICE for node in ast.walk(tree))
    return asks_the_count and follows_the_choice


def test_adr_tendenza_lunga_sulle_candele_giornaliere_the_parameter_belongs_to_the_source_for_every_adapter() -> None:
    assert (LONG_TREND.key, LONG_TREND.default, LONG_TREND.minimum, LONG_TREND.maximum) == ("tendenza_lunga", 0, 0, 1)
    assert LONG_TREND in INDICATORS.parameters
    assert LONG_TREND not in DECLARATION.parameters


@pytest.mark.parametrize(
    ("source", "naming"),
    [
        ('values = {"tendenza.variazione_7g": change}\n', True),
        ('key = f"variazione_{days}g"\n', True),
        ('values = {"lungo.timeframe": label}\n', False),
        ('values[f"variazione_percentuale_{label}"] = change\n', False),
    ],
)
def test_adr_tendenza_lunga_sulle_candele_giornaliere_a_trend_value_outside_the_domain_is_found(
    source: str, naming: bool
) -> None:
    assert names_a_trend_value(source) is naming


def test_adr_tendenza_lunga_sulle_candele_giornaliere_the_values_are_computed_only_in_the_domain() -> None:
    outside = [
        str(path.relative_to(ROOT))
        for path in ROOT.rglob("*.py")
        if not path.is_relative_to(DOMAIN) and names_a_trend_value(path.read_text(encoding="utf-8"))
    ]

    assert not outside, f"I valori della tendenza lunga si calcolano nel domain di sources: {outside}"


@pytest.mark.parametrize(
    ("source", "reading"),
    [
        (
            "def read(self):\n"
            "    if LongTrendChoice.of(settings).active:\n"
            "        return market.candles(asset, DAILY, DAILY_CANDLES, now)\n",
            True,
        ),
        ("def read(self):\n    return market.candles(asset, DAILY, DAILY_CANDLES, now)\n", False),
        (
            "def read(self):\n"
            "    if LongTrendChoice.of(settings).active:\n"
            "        return market.candles(asset, DAILY, 61, now)\n",
            False,
        ),
    ],
)
def test_adr_tendenza_lunga_sulle_candele_giornaliere_a_reader_that_ignores_the_choice_is_found(
    source: str, reading: bool
) -> None:
    assert reads_the_daily_candles_of_the_choice(source) is reading


def test_adr_tendenza_lunga_sulle_candele_giornaliere_the_reader_reads_the_daily_candles_the_choice_asks() -> None:
    assert reads_the_daily_candles_of_the_choice(READER.read_text(encoding="utf-8"))
