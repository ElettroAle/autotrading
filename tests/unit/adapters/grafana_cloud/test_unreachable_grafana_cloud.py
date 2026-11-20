"""ADR-telemetria-opentelemetry-verso-grafana-cloud: with Grafana Cloud unreachable the telemetry never blocks the
service. A request to the api and one to the worker answer at once while the export fails in the background, and the
queues of the processors stay bounded: what exceeds them is dropped, the memory does not grow.
"""

import json
import os
import socket
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

REPOSITORY = Path(__file__).resolve().parents[4]
TOKEN = "glc_secret-token"  # noqa: S105 - a made-up token of a fake stack
# Far below the ten seconds an OTLP export waits for an answer, far above a request served in memory.
REQUEST_DEADLINE_SECONDS = 3.0
# Many times the 2048 places of a queue: kept in memory they would weigh tens of megabytes.
RECORDS_BEYOND_THE_QUEUES = 30_000
MEMORY_GROWTH_LIMIT_BYTES = 5_000_000
# Ample for emitting them in memory, traced by tracemalloc; an export in the way would take hours.
LOAD_DEADLINE_SECONDS = 60.0
# A whole service in a process of its own: the providers of OpenTelemetry are global and can be set only once. It
# leaves with os._exit, because the shutdown at exit would wait for the export to the unreachable endpoint.
SERVICE = """
import json
import logging
import os
import sys
import threading
import time
import tracemalloc

from fastapi.testclient import TestClient
from opentelemetry import trace

from autotrading.adapters.configuration.source import ConfigurationSource
from autotrading.adapters.inbound.api.app import HealthReport, create_api
from autotrading.adapters.inbound.api.worker import create_worker_api
from autotrading.adapters.outbound.grafana_cloud.composition import grafana_cloud_telemetry_adapters
from autotrading.application.tenancy.resolve_tenant import ResolveTenantUseCase
from tests.fakes.tenant_repository import InMemoryTenantRepositoryAdapter
from tests.support.platform import Platform
from tests.support.worker import Worker

endpoint, token_file = sys.argv[1:3]
request_deadline, load_deadline, records = float(sys.argv[3]), float(sys.argv[4]), int(sys.argv[5])
logging.getLogger().setLevel(logging.INFO)
grafana_cloud_telemetry_adapters(
    ConfigurationSource({
        "APP_ENVIRONMENT": "dev",
        "GRAFANA_OTLP_ENDPOINT": endpoint,
        "GRAFANA_INSTANCE_ID": "1932769",
        "GRAFANA_OTLP_TOKEN_FILE": token_file,
    }),
    "autotrading-api",
)
operations = logging.getLogger("autotrading.load")
tracer = trace.get_tracer("autotrading.load")


def seconds_taken(action, deadline):
    started = time.monotonic()
    worker = threading.Thread(target=action, daemon=True)
    worker.start()
    worker.join(deadline)
    return None if worker.is_alive() else time.monotonic() - started


def api_request():
    api = create_api(
        HealthReport("1.0.0", "dev"), ResolveTenantUseCase(InMemoryTenantRepositoryAdapter()), Platform().for_tenant
    )
    assert TestClient(api).get("/health").status_code == 200


def worker_request():
    with TestClient(create_worker_api("worker-token", Worker().for_tenant)) as client:
        assert client.get("/health").status_code == 200


def emit(count):
    for number in range(count):
        with tracer.start_as_current_span("load"):
            operations.info("record %s", number)


def memory_growth():
    tracemalloc.start()
    emit(4096)
    before = tracemalloc.get_traced_memory()[0]
    emit(records)
    return tracemalloc.get_traced_memory()[0] - before


growth = []
result = {
    "api": seconds_taken(api_request, request_deadline),
    "worker": seconds_taken(worker_request, request_deadline),
    "load": seconds_taken(lambda: growth.append(memory_growth()), load_deadline),
}
result["growth"] = growth[0] if growth else None
print(json.dumps(result), flush=True)
os._exit(0)
"""


def _silent_endpoint() -> Iterator[str]:
    """Accepts the connection in the backlog of the kernel and never answers."""
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    listener.listen(128)
    try:
        yield f"http://127.0.0.1:{listener.getsockname()[1]}/otlp"
    finally:
        listener.close()


def _refusing_endpoint() -> Iterator[str]:
    """A port nobody listens on any more: every connection is refused."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    yield f"http://127.0.0.1:{port}/otlp"


@pytest.fixture(
    scope="module", params=[_silent_endpoint, _refusing_endpoint], ids=["never-answers", "refuses-the-connection"]
)
def unreachable_endpoint(request: pytest.FixtureRequest) -> Iterator[str]:
    yield from request.param()


@pytest.fixture(scope="module")
def service_run(unreachable_endpoint: str, tmp_path_factory: pytest.TempPathFactory) -> dict[str, float | None]:
    tmp_path = tmp_path_factory.mktemp("unreachable")
    token_file = tmp_path / "grafana_otlp_token"
    token_file.write_text(TOKEN, encoding="utf-8")
    script = tmp_path / "service.py"
    script.write_text(SERVICE, encoding="utf-8")
    environment = {**os.environ, "PYTHONPATH": str(REPOSITORY)}
    arguments = [unreachable_endpoint, str(token_file), str(REQUEST_DEADLINE_SECONDS)]
    arguments += [str(LOAD_DEADLINE_SECONDS), str(RECORDS_BEYOND_THE_QUEUES)]
    finished = subprocess.run(
        [sys.executable, str(script), *arguments],
        cwd=REPOSITORY,
        env=environment,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert finished.returncode == 0, finished.stderr
    measured: dict[str, float | None] = json.loads(finished.stdout.strip().splitlines()[-1])
    return measured


@pytest.mark.parametrize("service", ["api", "worker"])
def test_a_request_answers_without_waiting_for_the_export_to_an_unreachable_grafana_cloud(
    service_run: dict[str, float | None], service: str
) -> None:
    seconds = service_run[service]

    assert seconds is not None, f"la richiesta a {service} attende l'esportazione oltre {REQUEST_DEADLINE_SECONDS}s"
    assert seconds < REQUEST_DEADLINE_SECONDS


def test_spans_and_records_beyond_the_queues_are_dropped_without_growing_the_memory(
    service_run: dict[str, float | None],
) -> None:
    growth = service_run["growth"]

    assert service_run["load"] is not None, f"{RECORDS_BEYOND_THE_QUEUES} span e record attendono l'esportazione"
    assert growth is not None
    assert growth < MEMORY_GROWTH_LIMIT_BYTES, f"la memoria cresce di {growth} byte: le code non sono limitate"
