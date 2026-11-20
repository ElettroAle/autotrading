"""ADR-telemetria-opentelemetry-verso-grafana-cloud: api and worker export traces, metrics and logs with OpenTelemetry
to Grafana Cloud, directly in OTLP, from the adapter of Grafana Cloud alone: it is the only folder that imports
OpenTelemetry, the bootstrap installs it first in both services, the token is a read-only file the pipeline installs
like the token of the bot (ADR 0071), and the forecaster, which has no secrets (ADR 0107), stays out.
"""

import ast
import re
import tomllib
from pathlib import Path

import pytest

from tests.support.architecture import SOURCE_ROOT, TECHNOLOGY_LIBRARIES

ROOT = Path(SOURCE_ROOT)
REPOSITORY = ROOT.parents[1]
FOLDER = "adapters/outbound/grafana_cloud"
LIBRARY = "opentelemetry"
SCANNED = ("src", "tools", "forecaster")
INDEPENDENT_FOLDERS = "Una cartella di tecnologia non importa un'altra"
FORBIDDEN_IN_THE_CORE = "Domain e application non importano tecnologie"
COMPOSITION = "grafana_cloud_telemetry_adapters"
SERVICES = {"create_application": "autotrading-api", "create_worker_application": "autotrading-worker"}
COMPOSE = REPOSITORY / "deploy" / "compose.yaml"
PREPARE = REPOSITORY / "deploy" / "prepare-installation.sh"
INSTALL_TOKEN = REPOSITORY / "deploy" / "install-grafana-token.sh"
DEPLOY_ACTION = REPOSITORY / ".github" / "actions" / "ssh-deploy" / "action.yml"
RELEASE = REPOSITORY / ".github" / "workflows" / "reusable-release.yml"
SERVICE = re.compile(r"^  ([a-z_-]+):\n((?:    .*\n|\s*\n)*)", re.MULTILINE)
TOKEN_FILE = "GRAFANA_OTLP_TOKEN_FILE: /run/secrets/grafana_otlp_token"  # noqa: S105 - where the token is, not the token
PUBLIC_SETTINGS = ("GRAFANA_OTLP_ENDPOINT: ${GRAFANA_OTLP_ENDPOINT:-}", "GRAFANA_INSTANCE_ID: ${GRAFANA_INSTANCE_ID:-}")


def _imported_roots(source: str) -> set[str]:
    roots: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        if isinstance(node, ast.ImportFrom) and node.module is not None and node.level == 0:
            roots.add(node.module.split(".")[0])
    return roots


def library_violations(path: str, source: str) -> list[str]:
    """OpenTelemetry enters only the folder of Grafana Cloud, the integrated system it reaches."""
    if path.startswith(f"src/autotrading/{FOLDER}/") or LIBRARY not in _imported_roots(source):
        return []
    return [f"{path}: {LIBRARY} solo in src/autotrading/{FOLDER}"]


def _first_call_after_the_source(function: ast.FunctionDef) -> ast.Call | None:
    statements = iter(function.body)
    for statement in statements:
        if isinstance(statement, ast.Assign) and isinstance(statement.value, ast.Call):
            called = statement.value.func
            if isinstance(called, ast.Name) and called.id == "ConfigurationSource":
                following = next(statements, None)
                if isinstance(following, ast.Expr) and isinstance(following.value, ast.Call):
                    return following.value
                return None
    return None


def bootstrap_violations(source: str) -> list[str]:
    """Each service installs the telemetry first, so the instrumentations see every engine, client and application."""
    functions = {node.name: node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef)}
    found = []
    for name, service in SERVICES.items():
        call = _first_call_after_the_source(functions[name]) if name in functions else None
        installs = (
            call is not None
            and isinstance(call.func, ast.Name)
            and call.func.id == COMPOSITION
            and [argument.value for argument in call.args if isinstance(argument, ast.Constant)] == [service]
        )
        if not installs:
            found.append(f"{name}: {COMPOSITION}(source, {service!r}) subito dopo la ConfigurationSource")
    return found


def _services(compose: str) -> dict[str, str]:
    services = compose.split("\nservices:\n", 1)[1].split("\nsecrets:\n", 1)[0]
    return {match.group(1): match.group(2) for match in SERVICE.finditer(services)}


def compose_violations(compose: str) -> list[str]:
    """api and worker read the public settings and the token file; the forecaster gets neither."""
    services = _services(compose)
    found = []
    for name in ("api", "worker"):
        body = services.get(name, "")
        if not all(setting in body for setting in (*PUBLIC_SETTINGS, TOKEN_FILE, "      - grafana_otlp_token\n")):
            found.append(f"{name}: impostazioni pubbliche e file del token di Grafana Cloud")
    if "GRAFANA" in services.get("forecaster", "") or "grafana" in services.get("forecaster", ""):
        found.append("forecaster: nessun segreto, nemmeno il token di Grafana Cloud (ADR 0107)")
    if re.search(r"GRAFANA_OTLP_TOKEN(?!_FILE)", compose) or "OTEL_EXPORTER_OTLP_HEADERS" in compose:
        found.append("il token di Grafana Cloud arriva solo come file, mai in una variabile d'ambiente")
    if "  grafana_otlp_token:\n    file: ./secrets/grafana_otlp_token\n" not in compose:
        found.append("il segreto grafana_otlp_token è il file secrets/grafana_otlp_token della macchina")
    return found


CONFORMING_BOOTSTRAP = """
def create_application(configuration):
    source = ConfigurationSource(configuration)
    grafana_cloud_telemetry_adapters(source, "autotrading-api")
    engine = sqlalchemy_adapters(source)


def create_worker_application(configuration):
    source = ConfigurationSource(configuration)
    grafana_cloud_telemetry_adapters(source, "autotrading-worker")
"""
VIOLATING_BOOTSTRAPS = [
    CONFORMING_BOOTSTRAP.replace(
        '    grafana_cloud_telemetry_adapters(source, "autotrading-api")\n    engine = sqlalchemy_adapters(source)\n',
        '    engine = sqlalchemy_adapters(source)\n    grafana_cloud_telemetry_adapters(source, "autotrading-api")\n',
    ),
    CONFORMING_BOOTSTRAP.replace('    grafana_cloud_telemetry_adapters(source, "autotrading-worker")\n', ""),
    CONFORMING_BOOTSTRAP.replace('"autotrading-worker"', '"autotrading-api"'),
]
CONFORMING_COMPOSE = f"""name: autotrading

services:
  forecaster:
    image: ${{FORECASTER_IMAGE:-}}
  worker:
    environment:
      {PUBLIC_SETTINGS[0]}
      {PUBLIC_SETTINGS[1]}
      {TOKEN_FILE}
    secrets:
      - grafana_otlp_token
  api:
    environment:
      {PUBLIC_SETTINGS[0]}
      {PUBLIC_SETTINGS[1]}
      {TOKEN_FILE}
    secrets:
      - grafana_otlp_token

secrets:
  grafana_otlp_token:
    file: ./secrets/grafana_otlp_token
"""
VIOLATING_COMPOSES = [
    CONFORMING_COMPOSE.replace("    image: ${FORECASTER_IMAGE:-}\n", f"    environment:\n      {TOKEN_FILE}\n", 1),
    CONFORMING_COMPOSE.replace(f"      {TOKEN_FILE}\n", "", 1),
    CONFORMING_COMPOSE.replace("    secrets:\n      - grafana_otlp_token\n  api:", "  api:"),
    CONFORMING_COMPOSE.replace(TOKEN_FILE, "GRAFANA_OTLP_TOKEN: ${GRAFANA_OTLP_TOKEN:-}", 1),
    CONFORMING_COMPOSE.replace("    file: ./secrets/grafana_otlp_token\n", "    environment: GRAFANA_OTLP_TOKEN\n"),
]


@pytest.mark.parametrize(
    ("path", "source"),
    [
        ("src/autotrading/adapters/outbound/telegram/bot_api.py", "from opentelemetry import trace\n"),
        ("src/autotrading/bootstrap.py", "import opentelemetry.sdk\n"),
        ("src/autotrading/application/flows/run_cycle.py", "from opentelemetry.trace import get_tracer\n"),
        ("forecaster/service.py", "from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor\n"),
    ],
)
def test_opentelemetry_outside_the_grafana_cloud_folder_is_caught(path: str, source: str) -> None:
    assert library_violations(path, source)


def test_opentelemetry_inside_the_grafana_cloud_folder_breaks_no_rule() -> None:
    assert library_violations(f"src/autotrading/{FOLDER}/telemetry.py", "from opentelemetry import trace\n") == []


def test_the_repository_imports_opentelemetry_only_in_the_grafana_cloud_folder() -> None:
    found = [
        violation
        for folder in SCANNED
        for file in sorted((REPOSITORY / folder).rglob("*.py"))
        for violation in library_violations(file.relative_to(REPOSITORY).as_posix(), file.read_text(encoding="utf-8"))
    ]

    assert found == []


def test_the_grafana_cloud_folder_declares_opentelemetry_as_its_only_library() -> None:
    assert TECHNOLOGY_LIBRARIES[FOLDER] == frozenset({LIBRARY})
    assert all(LIBRARY not in libraries for folder, libraries in TECHNOLOGY_LIBRARIES.items() if folder != FOLDER)


def test_the_grafana_cloud_folder_is_independent_and_the_core_never_imports_opentelemetry() -> None:
    contracts = {
        contract["name"]: contract
        for contract in tomllib.loads((REPOSITORY / "pyproject.toml").read_text(encoding="utf-8"))["tool"][
            "importlinter"
        ]["contracts"]
    }

    assert "autotrading." + FOLDER.replace("/", ".") in contracts[INDEPENDENT_FOLDERS]["modules"]
    assert LIBRARY in contracts[FORBIDDEN_IN_THE_CORE]["forbidden_modules"]


@pytest.mark.parametrize("source", VIOLATING_BOOTSTRAPS)
def test_a_service_that_does_not_install_the_telemetry_first_is_caught(source: str) -> None:
    assert bootstrap_violations(source)


def test_a_bootstrap_that_installs_the_telemetry_first_breaks_no_rule() -> None:
    assert bootstrap_violations(CONFORMING_BOOTSTRAP) == []


def test_api_and_worker_install_the_telemetry_first() -> None:
    assert bootstrap_violations((ROOT / "bootstrap.py").read_text(encoding="utf-8")) == []


@pytest.mark.parametrize("compose", VIOLATING_COMPOSES)
def test_a_compose_that_misplaces_the_telemetry_settings_is_caught(compose: str) -> None:
    assert compose_violations(compose)


def test_a_compose_with_the_telemetry_of_api_and_worker_breaks_no_rule() -> None:
    assert compose_violations(CONFORMING_COMPOSE) == []


def test_the_compose_of_the_installation_gives_the_telemetry_to_api_and_worker_alone() -> None:
    assert compose_violations(COMPOSE.read_text(encoding="utf-8")) == []


def test_the_release_creates_the_empty_token_file_and_installs_the_token_from_stdin() -> None:
    """ADR 0071: created outside the machine, the token travels on stdin of Tailscale SSH and lands as a 0400 file."""
    prepare = PREPARE.read_text(encoding="utf-8")
    install = INSTALL_TOKEN.read_text(encoding="utf-8")

    assert ": > /secrets/grafana_otlp_token" in prepare
    assert "chown 65532:65532 /secrets/grafana_otlp_token && chmod 0400 /secrets/grafana_otlp_token" in prepare
    assert "--network none" in install
    assert 'chown 65532:65532 "$new" && chmod 0400 "$new" && mv -f "$new" "$current"' in install
    assert "touch .grafana_otlp_token_changed" in install


def test_the_release_passes_the_settings_and_the_token_and_recreates_api_and_worker_when_it_changes() -> None:
    action = DEPLOY_ACTION.read_text(encoding="utf-8")
    release = RELEASE.read_text(encoding="utf-8")

    assert "GRAFANA_OTLP_ENDPOINT=%s" in action
    assert "GRAFANA_INSTANCE_ID=%s" in action
    assert re.search(r"printf '%s' \"\$GRAFANA_OTLP_TOKEN\" \| ssh .*\n?.*install-grafana-token\.sh", action)
    assert re.search(r"if \[ -e \.grafana_otlp_token_changed \].*\n.*--force-recreate[^\n]* api worker", action)
    assert release.count("grafana-otlp-token: ${{ secrets.GRAFANA_OTLP_TOKEN }}") == 2
    assert release.count("grafana-otlp-endpoint: ${{ vars.GRAFANA_OTLP_ENDPOINT }}") == 2
    assert release.count("grafana-instance-id: ${{ vars.GRAFANA_INSTANCE_ID }}") == 2
