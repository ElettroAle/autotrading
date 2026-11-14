"""The dashboard is a static container served on /dashboard of the name of the installation (ADR 0117).

It runs read only, without secrets and with only the public configuration of the installation; it listens on the local
interface alone, and Tailscale Serve exposes it on /dashboard of the same HTTPS name as the API, both at the creation of
a machine and at every release.
"""

import re
from pathlib import Path

import pytest

REPOSITORY = Path(__file__).resolve().parents[2]
PUBLIC_CONFIGURATION = frozenset({"APP_ENVIRONMENT", "AUTH_ISSUER", "AUTH_CLIENT_ID", "AUTH_SCOPE"})
LOCAL_PORT = '- "127.0.0.1:8080:8080"'
HEALTH = "http://127.0.0.1:8080/dashboard/health"
SERVE = "serve --bg --https=443 --set-path=/dashboard http://127.0.0.1:8080/dashboard"
PINNED_IMAGE = re.compile(r"^FROM \S+@sha256:[0-9a-f]{64}( AS \S+)?$")
SERVICE_BLOCK = re.compile(r"^  dashboard:\n(?P<body>(?:    .*\n|\n)+)", re.MULTILINE)
VARIABLE = re.compile(r"^      (?P<name>[A-Z_]+):", re.MULTILINE)


def dashboard_service(compose: str) -> str:
    match = SERVICE_BLOCK.search(compose)
    return match["body"] if match else ""


def service_violations(service: str) -> list[str]:
    """The broken rules of the dashboard service of the compose."""
    found = []
    if "    read_only: true\n" not in service:
        found.append("il container della dashboard gira in sola lettura")
    if "    secrets:" in service:
        found.append("la dashboard non riceve segreti")
    if {match["name"] for match in VARIABLE.finditer(service)} - PUBLIC_CONFIGURATION:
        found.append(f"la dashboard riceve solo la configurazione pubblica {sorted(PUBLIC_CONFIGURATION)}")
    if re.findall(r"^      - \".*\"$", service, re.MULTILINE) != [f"      {LOCAL_PORT}"]:
        found.append("la dashboard ascolta solo sull'interfaccia locale, porta 8080")
    if HEALTH not in service:
        found.append(f"il compose attende la salute della dashboard su {HEALTH}")
    return found


CONFORMING_SERVICE = f"""    image: ${{DASHBOARD_IMAGE:-}}
    environment:
      APP_ENVIRONMENT: ${{APP_ENVIRONMENT:-}}
      AUTH_ISSUER: ${{AUTH_ISSUER:-}}
    read_only: true
    healthcheck:
      test: ["CMD", "node", "-e", "fetch('{HEALTH}')"]
    ports:
      {LOCAL_PORT}
"""
VIOLATING_SERVICES = [
    CONFORMING_SERVICE.replace("read_only: true", "read_only: false"),
    CONFORMING_SERVICE + "    secrets:\n      - worker_token\n",
    CONFORMING_SERVICE.replace("AUTH_ISSUER:", "WORKER_TOKEN_FILE:"),
    CONFORMING_SERVICE.replace("127.0.0.1:8080:8080", "8080:8080"),
    CONFORMING_SERVICE.replace("/dashboard/health", "/"),
]


@pytest.mark.parametrize("service", VIOLATING_SERVICES)
def test_each_rule_catches_its_violation(service: str) -> None:
    assert service_violations(service)


def test_a_conforming_service_breaks_no_rule() -> None:
    assert service_violations(CONFORMING_SERVICE) == []


def test_the_compose_runs_the_dashboard_as_decided() -> None:
    compose = (REPOSITORY / "deploy" / "compose.yaml").read_text(encoding="utf-8")

    assert service_violations(dashboard_service(compose)) == []


@pytest.mark.parametrize("path", ["deploy/cloud-init.yaml", "deploy/configure-serve.sh"])
def test_tailscale_serve_exposes_the_dashboard_on_its_path(path: str) -> None:
    assert SERVE in (REPOSITORY / path).read_text(encoding="utf-8")


def test_the_dashboard_image_is_a_pinned_stage_and_api_stays_the_default_target() -> None:
    dockerfile = (REPOSITORY / "Dockerfile").read_text(encoding="utf-8").splitlines()
    stages = [line for line in dockerfile if line.startswith("FROM")]

    assert [line for line in stages if line.endswith(" AS dashboard")]
    assert all(PINNED_IMAGE.match(line) for line in stages if "chainguard/node" in line)
    assert " AS " not in stages[-1]
