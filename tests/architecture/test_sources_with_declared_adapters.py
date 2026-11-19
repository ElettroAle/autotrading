"""ADR-fonti-con-adapter-dichiarati and ADR-migrazione-delle-fonti-al-modello-ad-adapter.

Every source of the catalog of the domain is offered by the adapters that declare themselves: each reading port of a
source asks its adapter for its declaration, a declaration is written only by an outbound adapter, and the names the
adapters declare never appear in domain, application or bootstrap. The sources of the flows before the adapters pass to
the new model with one correspondence, in the SQLAlchemy adapter, which the migration imports, which names only sources
of the catalog and adapters that declare themselves, and of which the strategy document keeps an identical copy because
an adapter folder cannot import another.
"""

import ast
from pathlib import Path

from autotrading.adapters.inbound.api import strategy_document
from autotrading.adapters.outbound.alternative_me import sentiment as alternative_me
from autotrading.adapters.outbound.coinmarketcap import sentiment as coinmarketcap
from autotrading.adapters.outbound.forecaster import price_forecast
from autotrading.adapters.outbound.hyperliquid import market_data
from autotrading.adapters.outbound.rss import news
from autotrading.adapters.outbound.sqlalchemy import source_correspondence
from autotrading.domain.sources.source_catalog import SOURCES
from tests.support.architecture import SourceModule, source_modules

REPOSITORY = Path(__file__).resolve().parents[2]
DECLARATION = "SourceAdapterDeclaration"
DECLARATION_METHOD = "declaration"
SOURCE_PORTS = frozenset({"SentimentPort", "NewsPort", "MarketDataPort", "PriceForecasterPort"})
SOURCE_PORTS_MODULE = "application/sources/ports.py"
MIGRATION = REPOSITORY / "migrations" / "versions" / "0050_sources_with_adapters.py"
CORRESPONDENCE_MODULE = "autotrading.adapters.outbound.sqlalchemy.source_correspondence"
DECLARED = (
    alternative_me.DECLARATION,
    coinmarketcap.DECLARATION,
    price_forecast.DECLARATION,
    market_data.DECLARATION,
    news.DECLARATION,
)

DECLARED_IN_THE_CORE = SourceModule.parse(
    "application/sources/list_sources.py",
    'SENTIMENT_ADAPTERS = (SourceAdapterDeclaration("alternative.me", "indice", (), (), offers_history=True),)\n',
)
NAMED_IN_THE_CORE = SourceModule.parse("domain/sources/sentiment.py", 'PREFERRED = "CoinMarketCap"\n')
PORT_WITHOUT_DECLARATION = SourceModule.parse(
    SOURCE_PORTS_MODULE,
    """
class NewsPort(Protocol):
    def read_latest(self) -> Sequence[NewsItem]: ...
""",
)
CONFORMING = (
    SourceModule.parse(
        "adapters/outbound/rss/news.py",
        'DECLARATION = SourceAdapterDeclaration("RSS", "feed", (), (), offers_history=False)\n',
    ),
    SourceModule.parse(
        SOURCE_PORTS_MODULE,
        """
class NewsPort(Protocol):
    def declaration(self) -> SourceAdapterDeclaration: ...

    def read_latest(self) -> Sequence[NewsItem]: ...
""",
    ),
)


def declarations_outside_the_adapters(modules: list[SourceModule]) -> list[str]:
    return [
        f"{module.path}:{node.lineno}: a source adapter declares itself only in adapters/outbound"
        for module in modules
        if not module.is_outbound_adapter
        for node in ast.walk(module.tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == DECLARATION
    ]


def ports_without_declaration(modules: list[SourceModule]) -> list[str]:
    return [
        f"{module.path}: {node.name} does not ask its adapter for its declaration"
        for module in modules
        if module.path == SOURCE_PORTS_MODULE
        for node in ast.walk(module.tree)
        if isinstance(node, ast.ClassDef) and node.name in SOURCE_PORTS
        if DECLARATION_METHOD not in {item.name for item in node.body if isinstance(item, ast.FunctionDef)}
    ]


def adapter_names_in_the_core(modules: list[SourceModule], names: frozenset[str]) -> list[str]:
    return [
        f"{module.path}:{node.lineno}: names the adapter {node.value!r}, which only its adapter declares"
        for module in modules
        if module.in_core or module.is_bootstrap
        for node in ast.walk(module.tree)
        if isinstance(node, ast.Constant) and node.value in names
    ]


def adapter_names() -> frozenset[str]:
    return frozenset(declared.name for declared in DECLARED)


def test_adr_fonti_con_adapter_dichiarati_every_reading_port_of_a_source_asks_for_the_declaration() -> None:
    assert ports_without_declaration([PORT_WITHOUT_DECLARATION]) == [
        f"{SOURCE_PORTS_MODULE}: NewsPort does not ask its adapter for its declaration"
    ]
    assert ports_without_declaration(list(CONFORMING)) == []
    assert ports_without_declaration(source_modules()) == []


def test_adr_fonti_con_adapter_dichiarati_only_an_outbound_adapter_declares_itself() -> None:
    assert declarations_outside_the_adapters([DECLARED_IN_THE_CORE]) == [
        "application/sources/list_sources.py:1: a source adapter declares itself only in adapters/outbound"
    ]
    assert declarations_outside_the_adapters(list(CONFORMING)) == []
    assert declarations_outside_the_adapters(source_modules()) == []


def test_adr_fonti_con_adapter_dichiarati_the_core_never_names_an_adapter() -> None:
    names = adapter_names()

    assert adapter_names_in_the_core([NAMED_IN_THE_CORE], names) == [
        "domain/sources/sentiment.py:1: names the adapter 'CoinMarketCap', which only its adapter declares"
    ]
    assert adapter_names_in_the_core(list(CONFORMING), names) == []
    assert adapter_names_in_the_core(source_modules(), names) == []


def test_adr_migrazione_delle_fonti_al_modello_ad_adapter_the_correspondence_names_declared_adapters() -> None:
    sources = {definition.name for definition in SOURCES}
    targets = set(source_correspondence.SOURCE_AND_ADAPTER.values())

    assert {source for source, _ in targets} <= sources
    assert {adapter for _, adapter in targets} <= adapter_names()


def test_adr_migrazione_delle_fonti_al_modello_ad_adapter_the_strategy_keeps_the_same_correspondence() -> None:
    assert strategy_document.SOURCE_AND_ADAPTER == source_correspondence.SOURCE_AND_ADAPTER


def test_adr_migrazione_delle_fonti_al_modello_ad_adapter_the_migration_imports_the_one_correspondence() -> None:
    tree = ast.parse(MIGRATION.read_text(encoding="utf-8"))

    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module == CORRESPONDENCE_MODULE
        for alias in node.names
    }
    own_names = {
        node.value for node in ast.walk(tree) if isinstance(node, ast.Constant) and node.value in adapter_names()
    }
    assert {"SOURCE_AND_ADAPTER", "migrated_document"} <= imported
    assert own_names == set()
