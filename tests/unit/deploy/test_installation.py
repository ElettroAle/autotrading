"""The release succeeds only when every service of the installation is healthy (Bug 189)."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
COMPOSE = ROOT / "deploy" / "compose.yaml"
DEPLOY_ACTION = ROOT / ".github" / "actions" / "ssh-deploy" / "action.yml"
PREPARE = ROOT / "deploy" / "prepare-installation.sh"
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
    assert {"postgres", "migrate", "forecaster", "worker", "api"} <= set(_services())


def test_the_installation_runs_no_litellm_proxy_and_keeps_none_of_its_secrets() -> None:
    """ADR 0150: the library runs inside the worker; the proxy, its master key and its configuration are gone."""
    compose = COMPOSE.read_text(encoding="utf-8")

    assert "litellm" not in _services()
    assert re.findall(r"LITELLM_(?:URL|MASTER_KEY)\w*|litellm_(?:master_key|config)", compose) == []
    assert "litellm" not in DEPLOY_ACTION.read_text(encoding="utf-8")


def test_a_release_removes_what_the_proxy_left_on_the_machine() -> None:
    """ADR 0150: --remove-orphans stops the old container, the script removes its files."""
    script = PREPARE.read_text(encoding="utf-8")

    assert re.search(r"rm -rf .*secrets/litellm_master_key secrets/litellm_config", script)
    assert "docker compose up -d --remove-orphans" in DEPLOY_ACTION.read_text(encoding="utf-8")


def test_every_read_only_service_has_a_writable_temporary_directory() -> None:
    """ADR 0154: a library may write a temporary file at import (litellm does); a read-only service needs /tmp."""
    without = [
        name
        for name, body in _services().items()
        if "read_only: true" in body and not re.search(r"tmpfs:\n\s+- /tmp\b", body)
    ]

    assert without == [], f"read-only services without a /tmp in tmpfs: {without}"


def test_every_variable_the_compose_file_reads_is_written_by_the_release() -> None:
    """Bug 285: compose reads its variables from the .env the release writes; one left out starts a service without
    it (HYPERLIQUID_NETWORK stopped api and worker)."""
    read = set(re.findall(r"\$\{([A-Z_][A-Z0-9_]*)(?::?-[^}]*)?\}", COMPOSE.read_text(encoding="utf-8")))
    written = set(re.findall(r"([A-Z_][A-Z0-9_]*)=%s", DEPLOY_ACTION.read_text(encoding="utf-8")))

    assert sorted(read - written) == []
