"""ADR-fonte-social-con-adapter-lunarcrush: the social source is a per-asset source of the catalog of the domain,
offered by the adapters of SocialPort and read by one reader for every adapter in the common construction of the
readers; the posts beyond the number asked are discarded in the domain; the LunarCrush adapter lives in its own folder,
reaches the API v4 with httpx alone, declares a secret key and its own number of posts without history, and is the
adapter the bootstrap passes to the sources of the installation.
"""

import ast
import tomllib
from pathlib import Path

import pytest

from autotrading.adapters.outbound.lunarcrush import social
from autotrading.domain.sources.social import POSTS, SOCIAL
from autotrading.domain.sources.source_catalog import SOURCES
from tests.support.architecture import SOURCE_ROOT, TECHNOLOGY_LIBRARIES

ROOT = Path(SOURCE_ROOT)
REPOSITORY = ROOT.parents[1]
FOLDER = "adapters/outbound/lunarcrush"
PACKAGE = "autotrading.adapters.outbound.lunarcrush"
READERS = ROOT / "application" / "sources" / "source_readers.py"
SOCIAL_READER_MODULE = ROOT / "application" / "sources" / "read_social.py"
BOOTSTRAP = ROOT / "bootstrap.py"
INDEPENDENT_FOLDERS = "Una cartella di tecnologia non importa un'altra"
SOCIAL_READER = "ReadSocialUseCase"
COMPOSITION = "lunarcrush_adapters"
DISCARD_OF_THE_DOMAIN = "most_relevant"


def calls_in(source: str, function_name: str, called: str) -> bool:
    """Whether the function of the module calls the name given."""
    functions = [node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef)]
    return any(
        isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == called
        for function in functions
        if function.name == function_name
        for node in ast.walk(function)
    )


def discards_in_the_domain(source: str) -> bool:
    """Whether the reader keeps the posts through the rule of the domain, without slicing them itself."""
    tree = ast.parse(source)
    uses_the_rule = any(
        isinstance(node, ast.Attribute) and node.attr == DISCARD_OF_THE_DOMAIN for node in ast.walk(tree)
    )
    slices = any(isinstance(node, ast.Slice) for node in ast.walk(tree))
    return uses_the_rule and not slices


def independent_folders() -> list[str]:
    document = tomllib.loads((REPOSITORY / "pyproject.toml").read_text(encoding="utf-8"))
    [contract] = [
        contract
        for contract in document["tool"]["importlinter"]["contracts"]
        if contract["name"] == INDEPENDENT_FOLDERS
    ]
    modules: list[str] = contract["modules"]
    return modules


@pytest.mark.parametrize(
    ("source", "registered"),
    [
        (
            "def readers_of(systems, forecasts, cycle_minutes):\n"
            "    readers = {}\n"
            "    for social in systems.socials:\n"
            "        readers[SOCIAL.name, social.declaration().name] = ReadSocialUseCase(social)\n"
            "    return readers\n",
            True,
        ),
        ("def readers_of(systems, forecasts, cycle_minutes):\n    return {}\n", False),
    ],
)
def test_adr_fonte_social_con_adapter_lunarcrush_a_missing_reader_is_found(source: str, registered: bool) -> None:
    assert calls_in(source, "readers_of", SOCIAL_READER) is registered


def test_adr_fonte_social_con_adapter_lunarcrush_the_social_source_is_per_asset_with_a_reader_per_adapter() -> None:
    assert SOCIAL in SOURCES
    assert SOCIAL.per_asset
    assert calls_in(READERS.read_text(encoding="utf-8"), "readers_of", SOCIAL_READER)


@pytest.mark.parametrize(
    ("source", "in_the_domain"),
    [
        ("def execute(self, command):\n    return snapshot.most_relevant(posts)\n", True),
        ("def execute(self, command):\n    return snapshot.posts[:posts]\n", False),
    ],
)
def test_adr_fonte_social_con_adapter_lunarcrush_a_discard_outside_the_domain_is_found(
    source: str, in_the_domain: bool
) -> None:
    assert discards_in_the_domain(source) is in_the_domain


def test_adr_fonte_social_con_adapter_lunarcrush_the_posts_beyond_the_number_are_discarded_in_the_domain() -> None:
    assert discards_in_the_domain(SOCIAL_READER_MODULE.read_text(encoding="utf-8"))
    adapter = ast.parse(Path(str(social.__file__)).read_text(encoding="utf-8"))
    assert not any(isinstance(node, ast.Slice) for node in ast.walk(adapter))


@pytest.mark.parametrize(
    ("source", "composed"),
    [
        (
            "def source_systems(hyperliquid, forecaster):\n"
            "    return SourceSystems(socials=(lunarcrush_adapters(),))\n",
            True,
        ),
        ("def source_systems(hyperliquid, forecaster):\n    return SourceSystems(socials=())\n", False),
    ],
)
def test_adr_fonte_social_con_adapter_lunarcrush_an_installation_without_lunarcrush_is_found(
    source: str, composed: bool
) -> None:
    assert calls_in(source, "source_systems", COMPOSITION) is composed


def test_adr_fonte_social_con_adapter_lunarcrush_the_installation_offers_the_lunarcrush_adapter() -> None:
    assert calls_in(BOOTSTRAP.read_text(encoding="utf-8"), "source_systems", COMPOSITION)


def test_adr_fonte_social_con_adapter_lunarcrush_the_folder_reaches_lunarcrush_with_httpx_alone() -> None:
    assert TECHNOLOGY_LIBRARIES[FOLDER] == frozenset({"httpx"})
    assert PACKAGE in independent_folders()
    assert {path.name for path in (ROOT / FOLDER).glob("*.py")} >= {"configuration.py", "composition.py"}


def test_adr_fonte_social_con_adapter_lunarcrush_the_adapter_declares_a_secret_key_and_its_number_of_posts() -> None:
    declaration = social.DECLARATION
    [posts] = declaration.parameters

    assert declaration.name == "LunarCrush"
    assert [(field.label, field.secret) for field in declaration.configuration_fields] == [("chiave API", True)]
    assert (posts.key, posts.default, posts.minimum, posts.maximum) == (POSTS, 5, 1, 20)
    assert not declaration.offers_history


def test_adr_fonte_social_con_adapter_lunarcrush_the_folder_has_its_rule_and_is_listed_in_the_contract() -> None:
    rule = (REPOSITORY / ".claude" / "rules" / "tech-lunarcrush.md").read_text(encoding="utf-8")
    contract = (REPOSITORY / "CLAUDE.md").read_text(encoding="utf-8")

    assert f"src/autotrading/{FOLDER}/**" in rule
    assert "lunarcrush/" in contract
    assert "tech-lunarcrush.md" in contract
