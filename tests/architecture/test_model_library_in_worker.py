"""ADR-0148: LiteLLM is a library of the worker alone, imported only by its adapter folder.

The library weighs about 200 MiB in the process that loads it: the API neither composes the LiteLLM gateway nor loads
the library, and asks the worker for its catalog instead (ADR 0149).
"""

import ast
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests.support.architecture import (
    SOURCE_ROOT,
    TECHNOLOGY_LIBRARIES,
    Rule,
    SourceModule,
    violations_of,
)

REPOSITORY = Path(__file__).resolve().parents[2]
LIBRARY = "litellm"
LIBRARY_FOLDER = "adapters/outbound/litellm"
COMPOSITION = "litellm_adapters"
API_FACTORY = "create_application"
WORKER_FACTORY = "create_worker_application"
LOADED_BY = """
import sys
from pathlib import Path
from tempfile import mkdtemp

from autotrading import bootstrap
from tests.support.installation import installation_configuration, worker_configuration

secrets = Path(mkdtemp())
if sys.argv[1] == "api":
    bootstrap.create_application(installation_configuration(secrets))
else:
    bootstrap.create_worker_application(worker_configuration(secrets))
print("litellm" in sys.modules)
"""


def _called_names(function: ast.FunctionDef) -> set[str]:
    return {
        node.func.id for node in ast.walk(function) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }


def compositions_of(source: str) -> dict[str, set[str]]:
    """The functions every factory of the bootstrap calls, by the name of the factory."""
    functions = [node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef)]
    return {function.name: _called_names(function) for function in functions}


def api_composes_the_library(source: str) -> bool:
    return COMPOSITION in compositions_of(source).get(API_FACTORY, set())


def test_adr_0148_the_library_belongs_to_its_adapter_folder_alone() -> None:
    owners = [folder for folder, libraries in TECHNOLOGY_LIBRARIES.items() if LIBRARY in libraries]

    assert owners == [LIBRARY_FOLDER]
    assert TECHNOLOGY_LIBRARIES[LIBRARY_FOLDER] == frozenset({LIBRARY})


@pytest.mark.parametrize(
    "path",
    ["adapters/outbound/worker/model_catalog.py", "adapters/inbound/api/worker.py", "application/agent/ask_agent.py"],
)
def test_adr_0148_the_library_outside_its_folder_is_a_violation(path: str) -> None:
    rules = {violation.rule for violation in violations_of(SourceModule.parse(path, "import litellm\n"))}

    assert Rule.LIBRARIES_IN_THEIR_FOLDER in rules


def test_adr_0148_the_library_inside_its_folder_breaks_no_rule() -> None:
    module = SourceModule.parse(f"{LIBRARY_FOLDER}/model_call.py", "lazy import litellm\n")

    assert [violation for violation in violations_of(module) if violation.rule is Rule.LIBRARIES_IN_THEIR_FOLDER] == []


@pytest.mark.parametrize(
    ("source", "composed"),
    [
        (f"def {API_FACTORY}(source):\n    gateways = {COMPOSITION}()\n", True),
        (f"def {API_FACTORY}(source):\n    return api({{**{COMPOSITION}(), **other()}})\n", True),
        (f"def {API_FACTORY}(source):\n    return api(worker_model_catalog_adapters(source))\n", False),
        (f"def {WORKER_FACTORY}(source):\n    models = {COMPOSITION}()\n", False),
    ],
)
def test_adr_0148_the_composition_of_the_library_in_the_api_is_found(source: str, composed: bool) -> None:
    assert api_composes_the_library(source) is composed


def test_adr_0148_only_the_worker_composes_the_litellm_gateway() -> None:
    compositions = compositions_of((SOURCE_ROOT / "bootstrap.py").read_text(encoding="utf-8"))

    assert COMPOSITION not in compositions[API_FACTORY]
    assert COMPOSITION in compositions[WORKER_FACTORY]


def _loads_the_library(service: str) -> bool:
    environment = os.environ | {"PYTHONPATH": os.pathsep.join([str(REPOSITORY), str(REPOSITORY / "src")])}
    completed = subprocess.run(
        [sys.executable, "-c", LOADED_BY, service],
        capture_output=True,
        check=True,
        cwd=REPOSITORY,
        env=environment,
        text=True,
        timeout=300,
    )
    return completed.stdout.strip().splitlines()[-1] == "True"


def test_adr_0148_the_api_process_never_loads_the_library() -> None:
    assert not _loads_the_library("api")


def test_adr_0148_the_worker_process_loads_the_library() -> None:
    assert _loads_the_library("worker")
