"""The telemetry of a service towards Grafana Cloud: traces of FastAPI, httpx and SQLAlchemy, their metrics and the
records of the standard logging, with no secret among what leaves the process (ADR
telemetria-opentelemetry-verso-grafana-cloud).
"""

import base64
import logging
from collections.abc import Iterator
from dataclasses import dataclass

import httpx
import pytest
import sqlalchemy
from fastapi.testclient import TestClient
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.logging.handler import LoggingHandler
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk._logs.export import InMemoryLogRecordExporter
from opentelemetry.sdk.metrics.export import InMemoryMetricReader, MetricsData
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import SpanKind

from autotrading.adapters.inbound.api.app import HealthReport, create_api
from autotrading.adapters.inbound.api.worker import create_worker_api
from autotrading.adapters.outbound.grafana_cloud.telemetry import (
    TelemetryProviders,
    basic_authorization,
    instrument_libraries,
    otlp_providers,
    telemetry_providers,
    telemetry_resource,
)
from autotrading.adapters.outbound.sqlalchemy.database import SqlAlchemyDatabaseAdapter
from autotrading.application.tenancy.resolve_tenant import ResolveTenantUseCase
from tests.fakes.tenant_repository import InMemoryTenantRepositoryAdapter
from tests.support.http_recorder import recording_server
from tests.support.platform import Platform
from tests.support.worker import Worker

BOT_CALL = "https://api.telegram.org/bot123456:SECRET-OF-THE-BOT/getUpdates"
SECRET_VALUE = "value-that-never-leaves"  # noqa: S105 - a made-up secret the tests look for


@dataclass(frozen=True, slots=True)
class Exported:
    providers: TelemetryProviders
    spans: InMemorySpanExporter
    metrics: InMemoryMetricReader
    logs: InMemoryLogRecordExporter

    def finished_spans(self) -> tuple[ReadableSpan, ...]:
        self.providers[0].force_flush()
        return self.spans.get_finished_spans()

    def metric_names(self) -> set[str]:
        data = self.metrics.get_metrics_data()
        assert isinstance(data, MetricsData)
        return {
            metric.name
            for resource in data.resource_metrics
            for scope in resource.scope_metrics
            for metric in scope.metrics
        }

    def exported_logs(self) -> list[tuple[str, int]]:
        self.providers[2].force_flush()
        return [
            (str(record.log_record.body), record.log_record.trace_id or 0) for record in self.logs.get_finished_logs()
        ]


def in_memory_telemetry() -> Exported:
    # The in-memory exporter of the logs of OpenTelemetry declares no return type on its constructor.
    logs = InMemoryLogRecordExporter()  # type: ignore[no-untyped-call]
    spans, metrics = InMemorySpanExporter(), InMemoryMetricReader()
    resource = telemetry_resource("autotrading-test", "1.0.0", "dev")
    return Exported(telemetry_providers(resource, spans, metrics, logs), spans, metrics, logs)


@pytest.fixture
def exported() -> Iterator[Exported]:
    telemetry = in_memory_telemetry()
    yield telemetry
    telemetry.providers[0].shutdown()
    telemetry.providers[1].shutdown()
    telemetry.providers[2].shutdown()


@pytest.fixture
def instrumented(exported: Exported) -> Iterator[Exported]:
    instrument_libraries(exported.providers)
    yield exported
    FastAPIInstrumentor().uninstrument()
    HTTPXClientInstrumentor().uninstrument()
    SQLAlchemyInstrumentor().uninstrument()
    root = logging.getLogger()
    for handler in [handler for handler in root.handlers if isinstance(handler, LoggingHandler)]:
        root.removeHandler(handler)


def test_the_authorization_is_basic_with_instance_and_token_in_base64() -> None:
    expected = base64.b64encode(b"1932769:glc_token").decode()

    assert basic_authorization("1932769", "glc_token") == {"Authorization": f"Basic {expected}"}


def test_the_resource_names_service_version_and_environment() -> None:
    attributes = telemetry_resource("autotrading-api", "1.4.0", "prod").attributes

    assert attributes["service.name"] == "autotrading-api"
    assert attributes["service.version"] == "1.4.0"
    assert attributes["deployment.environment"] == "prod"


def test_without_a_version_the_resource_declares_none() -> None:
    assert "service.version" not in telemetry_resource("autotrading-worker", None, "dev").attributes


@pytest.mark.parametrize("attribute", ["http.url", "url.full"])
def test_a_call_to_the_bot_api_leaves_no_span(exported: Exported, attribute: str) -> None:
    tracer = exported.providers[0].get_tracer("test")
    with tracer.start_as_current_span("GET", kind=SpanKind.CLIENT, attributes={attribute: BOT_CALL}) as span:
        recording = span.is_recording()

    assert not recording
    assert exported.finished_spans() == ()


@pytest.mark.parametrize("attribute", ["http.url", "url.full"])
def test_a_url_keeps_no_query_string(exported: Exported, attribute: str) -> None:
    tracer = exported.providers[0].get_tracer("test")
    url = f"https://pro-api.coinmarketcap.com/v1/quotes?symbol=BTC&key={SECRET_VALUE}"
    with tracer.start_as_current_span("GET", kind=SpanKind.CLIENT, attributes={attribute: url, "http.method": "GET"}):
        pass

    [span] = exported.finished_spans()
    assert span.attributes == {attribute: "https://pro-api.coinmarketcap.com/v1/quotes", "http.method": "GET"}


def test_a_span_without_a_url_is_kept_as_it_is(exported: Exported) -> None:
    tracer = exported.providers[0].get_tracer("test")
    with tracer.start_as_current_span("cycle", attributes={"flow": "1"}):
        pass

    [span] = exported.finished_spans()
    assert span.attributes == {"flow": "1"}


def test_the_spans_carry_the_resource_of_the_service(exported: Exported) -> None:
    with exported.providers[0].get_tracer("test").start_as_current_span("cycle"):
        pass

    [span] = exported.finished_spans()
    assert span.resource.attributes["service.name"] == "autotrading-test"


def test_an_httpx_call_is_traced_without_its_query_string_and_measured(instrumented: Exported) -> None:
    with recording_server() as server, httpx.Client() as client:
        client.get(f"{server.address}/quotes?key={SECRET_VALUE}", headers={"X-Api-Key": SECRET_VALUE})

    [span] = instrumented.finished_spans()
    assert span.kind is SpanKind.CLIENT
    assert span.attributes is not None
    assert span.attributes["http.url"] == f"{server.address}/quotes"
    assert SECRET_VALUE not in repr(dict(span.attributes))
    assert "http.client.duration" in instrumented.metric_names()


def test_a_query_is_traced_with_its_placeholders_and_never_its_values(instrumented: Exported) -> None:
    engine = sqlalchemy.create_engine("sqlite://")
    with engine.connect() as connection:
        connection.execute(sqlalchemy.text("select :value"), {"value": SECRET_VALUE})

    statements = [span.attributes.get("db.statement") for span in instrumented.finished_spans() if span.attributes]
    assert "select ?" in statements
    assert SECRET_VALUE not in repr([span.attributes for span in instrumented.finished_spans()])


@pytest.mark.usefixtures("instrumented")
def test_the_engine_of_the_platform_is_created_instrumented() -> None:
    engine = SqlAlchemyDatabaseAdapter("postgres", 5432, "autotrading", "autotrading_app", "unit-only").engine()

    assert len(engine.dispatch.before_cursor_execute) > 0


def test_the_api_of_the_platform_is_created_instrumented(instrumented: Exported) -> None:
    api = create_api(
        HealthReport("1.0.0", "dev"), ResolveTenantUseCase(InMemoryTenantRepositoryAdapter()), Platform().for_tenant
    )

    TestClient(api).get("/health", headers={"Authorization": f"Bearer {SECRET_VALUE}"})

    [server] = [span for span in instrumented.finished_spans() if span.kind is SpanKind.SERVER]
    assert server.attributes is not None
    assert server.attributes["http.route"] == "/health"
    assert SECRET_VALUE not in repr(dict(server.attributes))
    assert "http.server.duration" in instrumented.metric_names()


def test_the_internal_api_of_the_worker_is_created_instrumented(instrumented: Exported) -> None:
    with TestClient(create_worker_api("worker-token", Worker().for_tenant)) as client:
        client.get("/health")

    [server] = [span for span in instrumented.finished_spans() if span.kind is SpanKind.SERVER]
    assert server.attributes is not None
    assert server.attributes["http.route"] == "/health"


def test_the_records_of_the_logging_are_exported_from_info_with_the_current_trace(instrumented: Exported) -> None:
    operations = logging.getLogger("autotrading.telemetry-test")
    operations.setLevel(logging.DEBUG)
    with instrumented.providers[0].get_tracer("test").start_as_current_span("cycle") as span:
        operations.info("ciclo avviato")
        operations.debug("dettaglio non esportato")
        trace_id = span.get_span_context().trace_id

    assert instrumented.exported_logs() == [("ciclo avviato", trace_id)]


@pytest.mark.parametrize("logger", ["httpx", "httpcore.connection", "opentelemetry.exporter"])
def test_the_records_that_carry_urls_or_come_from_the_exporter_are_not_exported(
    instrumented: Exported, logger: str
) -> None:
    library = logging.getLogger(logger)
    library.setLevel(logging.INFO)
    try:
        library.warning("HTTP Request: GET %s", BOT_CALL)
    finally:
        library.setLevel(logging.NOTSET)

    assert instrumented.exported_logs() == []


def test_the_exporters_send_traces_metrics_and_logs_to_the_endpoint_with_the_authorization() -> None:
    with recording_server() as server:
        providers = otlp_providers(
            f"{server.address}/otlp", basic_authorization("1932769", "glc_token"), Resource.create({})
        )
        tracer, meter, logger = providers
        with tracer.get_tracer("test").start_as_current_span("cycle"):
            pass
        meter.get_meter("test").create_counter("cycles").add(1)
        handler = LoggingHandler(logger_provider=logger)
        handler.emit(logging.LogRecord("autotrading", logging.INFO, __file__, 1, "ciclo", None, None))
        tracer.shutdown()
        meter.shutdown()
        logger.shutdown()

    assert sorted(server.paths()) == ["/otlp/v1/logs", "/otlp/v1/metrics", "/otlp/v1/traces"]
    expected = "Basic " + base64.b64encode(b"1932769:glc_token").decode()
    assert {request.headers["authorization"] for request in server.requests} == {expected}
    assert {request.headers["content-type"] for request in server.requests} == {"application/x-protobuf"}
