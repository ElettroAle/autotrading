"""The forecaster service stays apart from the hexagon, and Prophet stays inside it (ADR 0107).

The service runs in its own container with its own dependencies: `autotrading` must not reach it nor it `autotrading`,
and the scientific libraries enter only the module of the service that speaks Prophet.
"""

import ast
from pathlib import Path

import pytest

REPOSITORY = Path(__file__).resolve().parents[2]
SERVICE = "forecaster"
PROPHET_MODULE = "forecaster/prophet_model.py"
PROPHET_LIBRARIES = frozenset({"prophet", "pandas", "cmdstanpy", "numpy"})
SCANNED = ("src", "tools", "tests", SERVICE)


def _imported_roots(source: str) -> set[str]:
    roots: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        if isinstance(node, ast.ImportFrom) and node.module is not None and node.level == 0:
            roots.add(node.module.split(".")[0])
    return roots


def violations(path: str, source: str) -> list[str]:
    """The broken rules of a module, by its path relative to the repository."""
    imported = _imported_roots(source)
    inside_service = path.startswith(f"{SERVICE}/")
    found = []
    if inside_service and imported & {"autotrading", "tests"}:
        found.append(f"{path}: il servizio forecaster non importa l'esagono né i test")
    if path.startswith(("src/", "tools/")) and SERVICE in imported:
        found.append(f"{path}: l'esagono raggiunge il forecaster solo via HTTP, dall'adapter forecaster")
    if path != PROPHET_MODULE and imported & PROPHET_LIBRARIES:
        found.append(f"{path}: {sorted(imported & PROPHET_LIBRARIES)} solo in {PROPHET_MODULE}")
    return found


VIOLATING = [
    ("forecaster/service.py", "from autotrading.domain.sources.price_forecast import PricePoint\n"),
    ("forecaster/models.py", "import tests.support.postgres\n"),
    ("src/autotrading/adapters/outbound/forecaster/price_forecast.py", "from forecaster.models import ModelKey\n"),
    ("tools/coverage_gate.py", "import forecaster\n"),
    ("forecaster/service.py", "import pandas\n"),
    ("src/autotrading/domain/sources/price_forecast.py", "from prophet import Prophet\n"),
    ("tests/unit/forecaster/test_models.py", "import numpy\n"),
]
CONFORMING = [
    ("forecaster/prophet_model.py", "import pandas\nfrom prophet import Prophet\n"),
    ("forecaster/service.py", "from forecaster.models import ForecastModels\nfrom fastapi import FastAPI\n"),
    ("src/autotrading/adapters/outbound/forecaster/price_forecast.py", "import httpx\n"),
    ("tests/unit/forecaster/test_models.py", "from forecaster.models import ForecastModels\n"),
]


@pytest.mark.parametrize(("path", "source"), VIOLATING)
def test_each_rule_catches_its_violation(path: str, source: str) -> None:
    assert violations(path, source)


@pytest.mark.parametrize(("path", "source"), CONFORMING)
def test_a_conforming_module_breaks_no_rule(path: str, source: str) -> None:
    assert violations(path, source) == []


def test_the_repository_keeps_the_forecaster_apart() -> None:
    found = [
        violation
        for folder in SCANNED
        for file in sorted((REPOSITORY / folder).rglob("*.py"))
        for violation in violations(file.relative_to(REPOSITORY).as_posix(), file.read_text(encoding="utf-8"))
    ]

    assert found == []
