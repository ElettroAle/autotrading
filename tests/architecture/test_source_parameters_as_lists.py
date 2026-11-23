"""ADR-parametri-delle-fonti-come-liste-libere: every period, horizon and window of the market sources is a list of
whole numbers declared once in the domain of the sources, with at most 8 values and a safety cap of 10000 for the
parameters in candles and 3650 for those in days; no source keeps a 0/1 flag; catalog, API and dashboard derive every
list from its declaration, so no key of a list parameter is written outside the domain of the sources.
"""

import re
from collections.abc import Iterator
from pathlib import Path

import pytest

from autotrading.adapters.outbound.alternative_me import sentiment as alternative_me
from autotrading.adapters.outbound.arkham import whale_transfers as arkham
from autotrading.adapters.outbound.binance import volumes as binance
from autotrading.adapters.outbound.coinmarketcap import sentiment as coinmarketcap
from autotrading.adapters.outbound.forecaster import price_forecast
from autotrading.adapters.outbound.hyperliquid import market_data
from autotrading.adapters.outbound.lunarcrush import social as lunarcrush
from autotrading.adapters.outbound.rss import news
from autotrading.domain.sources.source_catalog import SOURCES
from autotrading.domain.sources.source_list_parameter import DeclaredParameter, SourceListParameter
from tests.support.architecture import REPOSITORY_ROOT, SOURCE_ROOT

DOMAIN_OF_SOURCES = SOURCE_ROOT / "domain" / "sources"
DASHBOARD = REPOSITORY_ROOT / "dashboard" / "src"
DASHBOARD_TESTS = (DASHBOARD / "testing",)
MAXIMUM_VALUES = 8
CAP_OF_UNIT = {"_candele": 10000, "_periodi": 10000, "_giorni": 3650, "_minuti": 43200}
DECLARED = (
    alternative_me.DECLARATION,
    coinmarketcap.DECLARATION,
    price_forecast.DECLARATION,
    market_data.DECLARATION,
    news.DECLARATION,
    arkham.DECLARATION,
    binance.DECLARATION,
    lunarcrush.DECLARATION,
)
# The lists the requirement names, with the range of every value and the default list.
REQUIRED = {
    "medie_periodi": (2, 10000, (20, 50)),
    "rsi_periodi": (2, 10000, (7, 14)),
    "volume_relativo_candele": (2, 10000, ()),
    "tendenza_giorni": (1, 3650, ()),
    "canale_giorni": (2, 3650, ()),
    "fibonacci_candele": (10, 10000, ()),
    "gann_candele": (10, 10000, ()),
    "ciclo_candele": (10, 10000, ()),
    "orizzonti_minuti": (15, 43200, (15, 60)),
    "pivot_giorni": (1, 3650, (1,)),
}


def declared_parameters() -> Iterator[DeclaredParameter]:
    for source in SOURCES:
        yield from source.parameters
    for declaration in DECLARED:
        yield from declaration.parameters


def list_parameters() -> list[SourceListParameter]:
    return [each for each in declared_parameters() if isinstance(each, SourceListParameter)]


def cap_violation(parameter: SourceListParameter) -> str | None:
    """Why the list breaks the limits of the design, if it does: too many values, or a cap that is not of its unit."""
    if parameter.maximum_values != MAXIMUM_VALUES:
        return f"{parameter.key}: al massimo {MAXIMUM_VALUES} valori, non {parameter.maximum_values}"
    caps = [cap for unit, cap in CAP_OF_UNIT.items() if parameter.key.endswith(unit)]
    if caps != [parameter.maximum]:
        return f"{parameter.key}: il tetto dipende dall'unità del nome ({CAP_OF_UNIT}), non {parameter.maximum}"
    return None


def names_a_list_key(text: str, keys: frozenset[str]) -> bool:
    """Whether the text writes the key of a list parameter: only its declaration may."""
    return any(re.search(rf"\b{re.escape(key)}\b", text) is not None for key in keys)


def outside_the_declaration() -> Iterator[Path]:
    for path in SOURCE_ROOT.rglob("*.py"):
        if not path.is_relative_to(DOMAIN_OF_SOURCES):
            yield path
    for path in DASHBOARD.rglob("*.ts*"):
        if ".test." not in path.name and not any(path.is_relative_to(folder) for folder in DASHBOARD_TESTS):
            yield path


@pytest.mark.parametrize(
    ("parameter", "violating"),
    [
        (SourceListParameter("medie_periodi", "medie", (20,), 2, 10000), False),
        (SourceListParameter("tendenza_giorni", "tendenza", (), 1, 3650), False),
        (SourceListParameter("tendenza_giorni", "tendenza", (), 1, 10000), True),
        (SourceListParameter("fibonacci_candele", "fibonacci", (), 10, 500), True),
        (SourceListParameter("medie_periodi", "medie", (20,), 2, 10000, maximum_values=12), True),
        (SourceListParameter("finestre", "finestre", (), 1, 10000), True),
    ],
)
def test_adr_parametri_delle_fonti_come_liste_libere_a_list_beyond_the_limits_is_found(
    parameter: SourceListParameter, violating: bool
) -> None:
    assert (cap_violation(parameter) is not None) is violating


def test_adr_parametri_delle_fonti_come_liste_libere_every_list_keeps_the_limits_of_the_design() -> None:
    violations = [violation for violation in map(cap_violation, list_parameters()) if violation is not None]

    assert not violations, f"Limiti dei parametri a lista: {violations}"


def test_adr_parametri_delle_fonti_come_liste_libere_the_lists_of_the_requirement_are_declared() -> None:
    declared = {each.key: (each.minimum, each.maximum, each.default) for each in list_parameters()}

    assert declared == REQUIRED


def test_adr_parametri_delle_fonti_come_liste_libere_no_source_keeps_a_flag() -> None:
    flags = [
        each.key
        for each in declared_parameters()
        if not isinstance(each, SourceListParameter) and (each.minimum, each.maximum) == (0, 1)
    ]

    assert not flags, f"Un flag 0/1 diventa una lista vuota o piena: {flags}"


@pytest.mark.parametrize(
    ("text", "naming"),
    [
        ('if (parameter.key === "orizzonti_minuti") {\n', True),
        ('settings = {"medie_periodi": (20, 50)}\n', True),
        ("if (parameter.kind === 'list') {\n", False),
        ('values = {"breve.EMA20": average}\n', False),
    ],
)
def test_adr_parametri_delle_fonti_come_liste_libere_a_key_outside_the_declaration_is_found(
    text: str, naming: bool
) -> None:
    assert names_a_list_key(text, frozenset(REQUIRED)) is naming


def test_adr_parametri_delle_fonti_come_liste_libere_every_list_derives_from_its_declaration_alone() -> None:
    keys = frozenset(each.key for each in list_parameters())
    outside = [
        str(path.relative_to(REPOSITORY_ROOT))
        for path in outside_the_declaration()
        if names_a_list_key(path.read_text(encoding="utf-8"), keys)
    ]

    assert not outside, f"Un parametro a lista si dichiara solo nel domain delle fonti: {outside}"
