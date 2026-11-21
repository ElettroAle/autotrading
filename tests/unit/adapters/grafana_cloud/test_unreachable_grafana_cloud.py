"""ADR-telemetria-opentelemetry-verso-grafana-cloud: with Grafana Cloud unreachable the telemetry never blocks the
service. A request to the api and one to the worker answer at once while the export fails in the background, and the
queues of the processors stay bounded: what exceeds them is dropped (ADR-code-della-telemetria-provate-senza-tempi-ne-
memoria: the bound is proved in the same process, with exporters held still, with no threshold of time or memory).
"""

import json
import logging
import os
import socket
import subprocess
import sys
import threading
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from opentelemetry.instrumentation.logging.handler import LoggingHandler
from opentelemetry.sdk._logs import ReadableLogRecord
from opentelemetry.sdk._logs.export import LogRecordExporter, LogRecordExportResult
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

from autotrading.adapters.outbound.grafana_cloud.telemetry import (
    TelemetryProviders,
    telemetry_providers,
    telemetry_resource,
)

REPOSITORY = Path(__file__).resolve().parents[4]
TOKEN = "glc_secret-token"  # noqa: S105 - a made-up token of a fake stack
# Far below the ten seconds an OTLP export waits for an answer, far above a request served in memory.
REQUEST_DEADLINE_SECONDS = 3.0
# The places of a queue and the items an export takes at once, the defaults of the batch processors of OpenTelemetry.
QUEUE_CAPACITY = 2048
EXPORT_BATCH = 512
# Many times the places of a queue.
EMITTED_BEYOND_THE_QUEUES = 5 * QUEUE_CAPACITY
# A guard against an emission that waits for the export, not a measure of speed: emitting them in memory takes a
# fraction of it even on a loaded machine, and the test does not wait for it unless the emission is stuck.
STUCK_EMISSION_GUARD_SECONDS = 120.0
# A whole service in a process of its own: the providers of OpenTelemetry are global and can be set only once. It
# leaves with os._exit, because the shutdown at exit would wait for the export to the unreachable endpoint.
SERVICE = """
import json
import logging
import os
import sys
import threading
import time

from fastapi.testclient import TestClient

from autotrading.adapters.configuration.source import ConfigurationSource
from autotrading.adapters.inbound.api.app import HealthReport, create_api
from autotrading.adapters.inbound.api.worker import create_worker_api
from autotrading.adapters.outbound.grafana_cloud.composition import grafana_cloud_telemetry_adapters
from autotrading.application.tenancy.resolve_tenant import ResolveTenantUseCase
from tests.fakes.tenant_repository import InMemoryTenantRepositoryAdapter
from tests.support.platform import Platform
from tests.support.worker import Worker

endpoint, token_file, request_deadline = sys.argv[1], sys.argv[2], float(sys.argv[3])
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


result = {
    "api": seconds_taken(api_request, request_deadline),
    "worker": seconds_taken(worker_request, request_deadline),
}
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


@dataclass(slots=True)
class _Gate:
    """Holds every export still until the test opens it, as an endpoint that never answers; counts what passes."""

    opened: threading.Event = field(default_factory=threading.Event)
    passed: int = 0

    def pass_through(self, count: int) -> None:
        self.opened.wait()
        self.passed += count


class _StuckSpanExporter(SpanExporter):
    def __init__(self, gate: _Gate) -> None:
        self._gate = gate

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        self._gate.pass_through(len(spans))
        return SpanExportResult.SUCCESS


class _StuckLogRecordExporter(LogRecordExporter):
    def __init__(self, gate: _Gate) -> None:
        self._gate = gate

    def export(self, batch: Sequence[ReadableLogRecord]) -> LogRecordExportResult:
        self._gate.pass_through(len(batch))
        return LogRecordExportResult.SUCCESS

    def shutdown(self) -> None:
        self._gate.opened.set()

    def force_flush(self, timeout_millis: int = 30_000) -> bool:  # noqa: ARG002 - the signature of the exporters
        return True


@dataclass(frozen=True, slots=True)
class StuckTelemetry:
    providers: TelemetryProviders
    spans: _Gate
    records: _Gate
    operations: logging.Logger

    def emit(self, count: int) -> None:
        tracer = self.providers[0].get_tracer("autotrading.queues")
        for number in range(count):
            with tracer.start_as_current_span("queued"):
                self.operations.info("record %s", number)

    def release(self) -> tuple[int, int]:
        """Opens the exports and empties the queues: what reaches the exporters is what the processors kept."""
        self.spans.opened.set()
        self.records.opened.set()
        self.providers[0].force_flush()
        self.providers[2].force_flush()
        return self.spans.passed, self.records.passed


@pytest.fixture
def stuck_telemetry() -> Iterator[StuckTelemetry]:
    spans, records = _Gate(), _Gate()
    resource = telemetry_resource("autotrading-test", "1.0.0", "dev")
    providers = telemetry_providers(
        resource, _StuckSpanExporter(spans), InMemoryMetricReader(), _StuckLogRecordExporter(records)
    )
    operations = logging.getLogger("autotrading.queues")
    level, propagate = operations.level, operations.propagate
    operations.propagate = False
    operations.setLevel(logging.INFO)
    handler = LoggingHandler(level=logging.INFO, logger_provider=providers[2])
    operations.addHandler(handler)
    yield StuckTelemetry(providers, spans, records, operations)
    operations.removeHandler(handler)
    operations.setLevel(level)
    operations.propagate = propagate
    spans.opened.set()
    records.opened.set()
    for provider in providers:
        provider.shutdown()


@pytest.mark.parametrize("service", ["api", "worker"])
def test_a_request_answers_without_waiting_for_the_export_to_an_unreachable_grafana_cloud(
    service_run: dict[str, float | None], service: str
) -> None:
    seconds = service_run[service]

    assert seconds is not None, f"la richiesta a {service} attende l'esportazione oltre {REQUEST_DEADLINE_SECONDS}s"
    assert seconds < REQUEST_DEADLINE_SECONDS


def test_spans_and_records_beyond_the_queues_are_dropped_while_the_export_is_stuck(
    stuck_telemetry: StuckTelemetry,
) -> None:
    """ADR-code-della-telemetria-provate-senza-tempi-ne-memoria: the emission returns while every export is stuck, and
    what the processors keep is at most a queue and the batch already handed to the exporter.
    """
    emission = threading.Thread(target=stuck_telemetry.emit, args=(EMITTED_BEYOND_THE_QUEUES,), daemon=True)
    emission.start()
    emission.join(STUCK_EMISSION_GUARD_SECONDS)

    assert not emission.is_alive(), f"{EMITTED_BEYOND_THE_QUEUES} span e record attendono l'esportazione bloccata"
    kept_spans, kept_records = stuck_telemetry.release()
    assert QUEUE_CAPACITY <= kept_spans <= QUEUE_CAPACITY + EXPORT_BATCH, f"{kept_spans} span trattenuti"
    assert QUEUE_CAPACITY <= kept_records <= QUEUE_CAPACITY + EXPORT_BATCH, f"{kept_records} record trattenuti"
