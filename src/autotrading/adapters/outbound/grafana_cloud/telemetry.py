import base64
import logging
from collections.abc import Mapping, Sequence
from urllib.parse import urlsplit, urlunsplit

from opentelemetry import _logs, metrics, trace
from opentelemetry.context import Context
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.logging.handler import LoggingHandler
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor, LogRecordExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import MetricReader, PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanExporter
from opentelemetry.sdk.trace.sampling import ALWAYS_ON, Decision, ParentBased, Sampler, SamplingResult
from opentelemetry.trace import Link, SpanKind
from opentelemetry.trace.span import TraceState
from opentelemetry.util.types import Attributes

type TelemetryProviders = tuple[TracerProvider, MeterProvider, LoggerProvider]

EXPORT_INTERVAL_MILLISECONDS = 60_000
TRACES_PATH = "/v1/traces"
METRICS_PATH = "/v1/metrics"
LOGS_PATH = "/v1/logs"
URL_ATTRIBUTES = frozenset({"http.url", "url.full"})
# The Bot API carries the token of the bot in the path of every call (tech-telegram.md): its calls leave no span.
UNTRACED_HOSTS = frozenset({"api.telegram.org"})
# Their records carry whole addresses, the token of the bot among them, or would feed the exporter its own failures.
UNEXPORTED_LOGGERS = ("httpx", "httpcore", "opentelemetry")


class _ConfidentialSampler(Sampler):
    """Every trace, as its parent decides, but no span for a call whose address carries a secret, and every other
    address without its query string, where the keys of the services travel.
    """

    def __init__(self) -> None:
        self._parent = ParentBased(ALWAYS_ON)

    def should_sample(  # noqa: PLR0913, PLR0917 - the signature of the samplers of OpenTelemetry
        self,
        parent_context: Context | None,
        trace_id: int,
        name: str,
        kind: SpanKind | None = None,
        attributes: Attributes = None,
        links: Sequence[Link] | None = None,
        trace_state: TraceState | None = None,
    ) -> SamplingResult:
        if any(urlsplit(url).hostname in UNTRACED_HOSTS for url in _urls_of(attributes)):
            return SamplingResult(Decision.DROP)
        confidential = _without_query_strings(attributes)
        return self._parent.should_sample(parent_context, trace_id, name, kind, confidential, links, trace_state)

    def get_description(self) -> str:
        return "ConfidentialSampler"


def basic_authorization(instance_id: str, token: str) -> dict[str, str]:
    """The header Grafana Cloud authenticates an OTLP export with: the instance and the token, in base64."""
    credentials = base64.b64encode(f"{instance_id}:{token}".encode()).decode()
    return {"Authorization": f"Basic {credentials}"}


def telemetry_resource(service_name: str, version: str | None, environment: str) -> Resource:
    declared = {"service.name": service_name, "service.version": version, "deployment.environment": environment}
    return Resource.create({name: value for name, value in declared.items() if value is not None})


def otlp_providers(endpoint: str, headers: Mapping[str, str], resource: Resource) -> TelemetryProviders:
    """Providers exporting in OTLP HTTP/protobuf straight to the endpoint: no collector runs on the machine."""
    authorization = dict(headers)
    metric_exporter = OTLPMetricExporter(endpoint=endpoint + METRICS_PATH, headers=authorization)
    return telemetry_providers(
        resource,
        OTLPSpanExporter(endpoint=endpoint + TRACES_PATH, headers=authorization),
        PeriodicExportingMetricReader(metric_exporter, export_interval_millis=EXPORT_INTERVAL_MILLISECONDS),
        OTLPLogExporter(endpoint=endpoint + LOGS_PATH, headers=authorization),
    )


def telemetry_providers(
    resource: Resource, spans: SpanExporter, metric_reader: MetricReader, logs: LogRecordExporter
) -> TelemetryProviders:
    tracer = TracerProvider(resource=resource, sampler=_ConfidentialSampler())
    tracer.add_span_processor(BatchSpanProcessor(spans))
    logger = LoggerProvider(resource=resource)
    logger.add_log_record_processor(BatchLogRecordProcessor(logs))
    return tracer, MeterProvider(resource=resource, metric_readers=[metric_reader]), logger


def install_telemetry(providers: TelemetryProviders) -> None:
    tracer, meter, logger = providers
    trace.set_tracer_provider(tracer)
    metrics.set_meter_provider(meter)
    _logs.set_logger_provider(logger)
    instrument_libraries(providers)


def instrument_libraries(providers: TelemetryProviders) -> None:
    """Traces and metrics of FastAPI, httpx and SQLAlchemy, and the records of the standard logging from INFO."""
    tracer, meter, logger = providers
    FastAPIInstrumentor().instrument(tracer_provider=tracer, meter_provider=meter)
    HTTPXClientInstrumentor().instrument(tracer_provider=tracer, meter_provider=meter)
    # Declared up to SQLAlchemy 2.0, it traces the 2.1 of the platform as well: the unit tests of the adapter prove it.
    SQLAlchemyInstrumentor().instrument(tracer_provider=tracer, meter_provider=meter, skip_dep_check=True)
    logging.getLogger().addHandler(_exported_records(logger))


def _exported_records(logger: LoggerProvider) -> logging.Handler:
    handler = LoggingHandler(level=logging.INFO, logger_provider=logger)
    handler.addFilter(_exportable)
    return handler


def _exportable(record: logging.LogRecord) -> bool:
    return not any(record.name == name or record.name.startswith(f"{name}.") for name in UNEXPORTED_LOGGERS)


def _urls_of(attributes: Attributes) -> list[str]:
    if attributes is None:
        return []
    return [value for name, value in attributes.items() if name in URL_ATTRIBUTES and isinstance(value, str)]


def _without_query_strings(attributes: Attributes) -> Attributes:
    if attributes is None:
        return None
    return {
        name: _without_query(value) if name in URL_ATTRIBUTES and isinstance(value, str) else value
        for name, value in attributes.items()
    }


def _without_query(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))
