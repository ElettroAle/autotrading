"""The release succeeds only when every service of the installation is healthy (Bug 189)."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
COMPOSE = ROOT / "deploy" / "compose.yaml"
DEPLOY_ACTION = ROOT / ".github" / "actions" / "ssh-deploy" / "action.yml"
SERVICE = re.compile(r"^  ([a-z_-]+):\n((?:    .*\n|\s*\n)*)", re.MULTILINE)
# A one-shot service is ready when it exits successfully, as its dependants require; it has no health to check.
ONE_SHOT = 'restart: "no"'


def _services() -> dict[str, str]:
    text = COMPOSE.read_text(encoding="utf-8")
    services = text.split("\nservices:\n", 1)[1].split("\nsecrets:\n", 1)[0]
    return {match.group(1): match.group(2) for match in SERVICE.finditer(services)}


def test_every_long_running_service_declares_its_health() -> None:
    unchecked = [name for name, body in _services().items() if ONE_SHOT not in body and "healthcheck:" not in body]

    assert unchecked == [], f"services without a healthcheck: {unchecked}"


def test_every_start_of_the_installation_waits_for_the_services_to_be_healthy() -> None:
    starts = re.findall(r"docker compose up -d[^\n']*", DEPLOY_ACTION.read_text(encoding="utf-8"))

    assert starts
    assert [start for start in starts if not re.search(r"--wait --wait-timeout \d+", start)] == []


def test_the_services_are_found_in_the_compose_file() -> None:
    assert {"postgres", "migrate", "litellm", "forecaster", "worker", "api"} <= set(_services())
