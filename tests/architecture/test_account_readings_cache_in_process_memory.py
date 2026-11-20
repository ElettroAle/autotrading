"""ADR-cache-delle-letture-del-conto-come-decorator-in-memoria: in the API process the reading of an account goes
through a decorator of AccountActivityPort, in its own folder `process_memory/`, whose store the composition creates
once; the worker never mounts it, so the cycles always read the exchange (Bug 635).
"""

import ast
from collections.abc import Iterator

import pytest

from autotrading.adapters.outbound.process_memory.account_activity import ProcessMemoryAccountActivityAdapter
from autotrading.adapters.outbound.process_memory.configuration import _ProcessMemorySettings
from autotrading.application.flows.ports import AccountActivityPort
from tests.support.architecture import SOURCE_ROOT, TECHNOLOGY_LIBRARIES, Rule, SourceModule, violations_of

FOLDER = "adapters/outbound/process_memory"
COMPOSITION = "process_memory_adapters"
DECORATOR = "ProcessMemoryAccountActivityAdapter"
STORE = "_AccountActivityStore"
API_FACTORY = "create_application"
WORKER_FACTORY = "create_worker_application"

DECORATOR_OF_THE_SAME_PORT = f"""
from autotrading.application.flows.ports import AccountActivityPort

class {DECORATOR}(AccountActivityPort):
    def __init__(self, decorated: AccountActivityPort, tenant_id: TenantId, store: {STORE}) -> None: ...
"""
CACHE_RECEIVING_ANOTHER_PORT = f"""
from autotrading.application.flows.ports import AccountActivityPort, FlowLedgerPort

class {DECORATOR}(AccountActivityPort):
    def __init__(self, decorated: AccountActivityPort, ledger: FlowLedgerPort, store: {STORE}) -> None: ...
"""
CACHE_NOT_DECLARING_THE_PORT = f"""
from autotrading.application.flows.ports import AccountActivityPort

class {DECORATOR}:
    def __init__(self, decorated: AccountActivityPort, store: {STORE}) -> None: ...
"""
STORE_IN_A_MODULE_VARIABLE = f"_STORE = {STORE}(10.0)\n"
STORE_OF_THE_COMPOSITION = f"def {COMPOSITION}():\n    store = {STORE}(10.0)\n"


def _functions(source: str) -> dict[str, ast.FunctionDef]:
    return {node.name: node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef)}


def _called(function: ast.FunctionDef) -> set[str]:
    return {node.id for node in ast.walk(function) if isinstance(node, ast.Name)}


def reached_from(source: str, factory: str) -> set[str]:
    """Every name the factory uses, also through the functions of the same module it calls."""
    functions = _functions(source)
    reached: set[str] = set()
    pending = [factory]
    while pending:
        name = pending.pop()
        if name in reached:
            continue
        reached.add(name)
        if name in functions:
            pending.extend(_called(functions[name]) - reached)
    return reached


def module_level_stores(source: str) -> Iterator[str]:
    """The stores created outside any function: state the composition does not own."""
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign | ast.AnnAssign) and STORE in ast.unparse(node.value or node):
            yield ast.unparse(node)


def orchestration_of(path: str, source: str) -> list[Rule]:
    return [
        violation.rule
        for violation in violations_of(SourceModule.parse(path, source))
        if violation.rule is Rule.ADAPTERS_DO_NOT_ORCHESTRATE
    ]


def test_adr_cache_delle_letture_del_conto_the_api_mounts_the_cache() -> None:
    bootstrap = (SOURCE_ROOT / "bootstrap.py").read_text(encoding="utf-8")

    assert COMPOSITION in reached_from(bootstrap, API_FACTORY)


def test_adr_cache_delle_letture_del_conto_the_worker_never_mounts_it() -> None:
    bootstrap = (SOURCE_ROOT / "bootstrap.py").read_text(encoding="utf-8")

    reached = reached_from(bootstrap, WORKER_FACTORY)

    assert COMPOSITION not in reached
    assert DECORATOR not in reached


@pytest.mark.parametrize(
    ("source", "mounted"),
    [
        (f"def {WORKER_FACTORY}(source):\n    return cycles(source)\ndef cycles(source):\n    {COMPOSITION}()\n", True),
        (f"def {WORKER_FACTORY}(source):\n    return cycles(source)\ndef cycles(source):\n    return source\n", False),
    ],
)
def test_adr_cache_delle_letture_del_conto_a_cache_mounted_by_the_worker_is_found(source: str, mounted: bool) -> None:
    assert (COMPOSITION in reached_from(source, WORKER_FACTORY)) is mounted


def test_adr_cache_delle_letture_del_conto_the_cache_is_a_decorator_of_the_same_port() -> None:
    module = SOURCE_ROOT / FOLDER / "account_activity.py"

    assert AccountActivityPort in ProcessMemoryAccountActivityAdapter.__bases__
    assert orchestration_of(f"{FOLDER}/account_activity.py", module.read_text(encoding="utf-8")) == []


def test_adr_cache_delle_letture_del_conto_a_cache_that_is_not_a_decorator_is_a_violation() -> None:
    path = f"{FOLDER}/account_activity.py"

    assert orchestration_of(path, DECORATOR_OF_THE_SAME_PORT) == []
    assert orchestration_of(path, CACHE_RECEIVING_ANOTHER_PORT) == [Rule.ADAPTERS_DO_NOT_ORCHESTRATE]
    assert orchestration_of(path, CACHE_NOT_DECLARING_THE_PORT) == [Rule.ADAPTERS_DO_NOT_ORCHESTRATE]


def test_adr_cache_delle_letture_del_conto_the_folder_needs_no_library() -> None:
    assert TECHNOLOGY_LIBRARIES[FOLDER] == frozenset()


def test_adr_cache_delle_letture_del_conto_the_store_is_created_by_the_composition_only() -> None:
    sources = [path.read_text(encoding="utf-8") for path in (SOURCE_ROOT / FOLDER).glob("*.py")]

    assert [store for source in sources for store in module_level_stores(source)] == []
    assert STORE in ast.unparse(
        _functions((SOURCE_ROOT / FOLDER / "composition.py").read_text(encoding="utf-8"))[COMPOSITION]
    )


def test_adr_cache_delle_letture_del_conto_a_store_in_a_module_variable_is_found() -> None:
    assert list(module_level_stores(STORE_IN_A_MODULE_VARIABLE)) == [f"_STORE = {STORE}(10.0)"]
    assert list(module_level_stores(STORE_OF_THE_COMPOSITION)) == []


def test_adr_cache_delle_letture_del_conto_a_reading_stays_valid_ten_seconds() -> None:
    assert _ProcessMemorySettings().account_activity_validity_seconds == 10.0
