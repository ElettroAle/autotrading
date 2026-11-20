"""ADR-metadati-di-mercato-hyperliquid-riusati-dal-client-unico: one client of the SDK for the process, created by the
composition and shared by every adapter of the folder; each client of the library is built with the market metadata
already read, kept for an hour by a decorator private to the folder (Bug 635).
"""

import ast
import inspect
from collections.abc import Iterator

from autotrading.adapters.outbound.hyperliquid.configuration import _HyperliquidMetadataSettings
from autotrading.adapters.outbound.hyperliquid.market_metadata import _CachedMarketMetadata, _MarketMetadata
from tests.support.architecture import SOURCE_ROOT

FOLDER = SOURCE_ROOT / "adapters" / "outbound" / "hyperliquid"
COMPOSITION = "hyperliquid_adapters"
CLIENT = "HyperliquidSdkAdapter"
CACHE = "_CachedMarketMetadata"
READING = "_MarketMetadata"
LIBRARY_CLIENTS = frozenset({"Info", "Exchange"})
METADATA_ARGUMENTS = frozenset({"meta", "spot_meta"})
SHARED = "sdk"

CLIENT_WITH_METADATA = "Info(url, skip_ws=True, meta=metadata.meta, spot_meta=metadata.spot_meta, timeout=timeout)\n"
CLIENT_DOWNLOADING_THEM = "Exchange(wallet, url, account_address=address, timeout=timeout)\n"
SHARED_CLIENT = f"""
def {COMPOSITION}():
    sdk = {CLIENT}({CACHE}({READING}(), 3600.0))
    return ({{"a": FirstAdapter(sdk=sdk)}}, SecondAdapter.for_network(testnet=False, sdk=sdk))
"""
CLIENT_OF_ITS_OWN = f"""
def {COMPOSITION}():
    sdk = {CLIENT}({CACHE}({READING}(), 3600.0))
    return ({{"a": FirstAdapter(sdk=sdk)}}, SecondAdapter.for_network(testnet=False))
"""
CLIENT_WITHOUT_CACHE = f"""
def {COMPOSITION}():
    sdk = {CLIENT}()
    return (FirstAdapter(sdk=sdk),)
"""


def _sources() -> dict[str, str]:
    return {path.name: path.read_text(encoding="utf-8") for path in FOLDER.glob("*.py")}


def _name_of(call: ast.Call) -> str:
    if isinstance(call.func, ast.Name):
        return call.func.id
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    return ""


def library_clients_without_metadata(source: str) -> Iterator[str]:
    """The clients of the library built without both metadata: the library downloads them in its constructor."""
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call) or _name_of(node) not in LIBRARY_CLIENTS:
            continue
        if not {keyword.arg for keyword in node.keywords} >= METADATA_ARGUMENTS:
            yield ast.unparse(node)


def _composition(source: str) -> ast.FunctionDef:
    return next(
        node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef) and node.name == COMPOSITION
    )


def adapters_without_the_shared_client(source: str) -> list[str]:
    """The adapters the composition builds without the client of the process."""
    adapters = [
        node
        for node in ast.walk(_composition(source))
        if isinstance(node, ast.Call) and _builds_an_adapter(node) and _name_of(node) != CLIENT
    ]
    return [ast.unparse(call) for call in adapters if not _takes_the_shared_client(call)]


def _builds_an_adapter(call: ast.Call) -> bool:
    return _name_of(call).endswith("Adapter") or _name_of(call) == "for_network"


def _takes_the_shared_client(call: ast.Call) -> bool:
    arguments = [*call.args, *(keyword.value for keyword in call.keywords)]
    return any(isinstance(argument, ast.Name) and argument.id == SHARED for argument in arguments)


def clients_of_the_composition(source: str) -> list[str]:
    """The clients of the SDK the composition creates, with what they take."""
    return [
        ast.unparse(node)
        for node in ast.walk(_composition(source))
        if isinstance(node, ast.Call) and _name_of(node) == CLIENT
    ]


def _names_the_metadata(source: str) -> bool:
    return READING in source or CACHE in source


def test_adr_metadati_di_mercato_every_client_of_the_library_takes_the_metadata() -> None:
    found = {name: list(library_clients_without_metadata(source)) for name, source in _sources().items()}

    assert {name: clients for name, clients in found.items() if clients} == {}


def test_adr_metadati_di_mercato_a_client_that_downloads_the_metadata_is_found() -> None:
    assert list(library_clients_without_metadata(CLIENT_WITH_METADATA)) == []
    assert list(library_clients_without_metadata(CLIENT_DOWNLOADING_THEM)) == [CLIENT_DOWNLOADING_THEM.strip()]


def test_adr_metadati_di_mercato_the_composition_creates_one_client_with_the_kept_metadata() -> None:
    composition = _sources()["composition.py"]

    assert clients_of_the_composition(composition) == [f"{CLIENT}(metadata)"]
    assert f"metadata = {CACHE}({READING}()" in ast.unparse(_composition(composition))


def test_adr_metadati_di_mercato_a_client_without_the_kept_metadata_is_found() -> None:
    assert clients_of_the_composition(CLIENT_WITHOUT_CACHE) == [f"{CLIENT}()"]


def test_adr_metadati_di_mercato_every_adapter_shares_the_client_of_the_process() -> None:
    assert adapters_without_the_shared_client(_sources()["composition.py"]) == []


def test_adr_metadati_di_mercato_an_adapter_with_a_client_of_its_own_is_found() -> None:
    assert adapters_without_the_shared_client(SHARED_CLIENT) == []
    assert adapters_without_the_shared_client(CLIENT_OF_ITS_OWN) == ["SecondAdapter.for_network(testnet=False)"]


def test_adr_metadati_di_mercato_the_cache_decorates_the_reading_of_the_metadata() -> None:
    parameters = inspect.signature(_CachedMarketMetadata.__init__).parameters

    assert _MarketMetadata in _CachedMarketMetadata.__bases__
    assert parameters["decorated"].annotation is _MarketMetadata


def test_adr_metadati_di_mercato_the_metadata_stay_private_to_the_folder() -> None:
    outside = [
        str(path.relative_to(SOURCE_ROOT))
        for path in SOURCE_ROOT.rglob("*.py")
        if FOLDER not in path.parents and _names_the_metadata(path.read_text(encoding="utf-8"))
    ]

    assert outside == []


def test_adr_metadati_di_mercato_no_module_keeps_metadata_outside_the_composition() -> None:
    module_level = [
        ast.unparse(node)
        for source in _sources().values()
        for node in ast.parse(source).body
        if isinstance(node, ast.Assign | ast.AnnAssign) and CACHE in ast.unparse(node)
    ]

    assert module_level == []


def test_adr_metadati_di_mercato_the_metadata_stay_valid_an_hour() -> None:
    assert _HyperliquidMetadataSettings().validity_seconds == 3600.0
