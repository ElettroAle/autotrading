"""The telemetry a service installs from its configuration: exported to Grafana Cloud with the three settings, off
without any of them (ADR telemetria-opentelemetry-verso-grafana-cloud).
"""

import logging
import subprocess
import sys
from pathlib import Path

import pytest
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.logging.handler import LoggingHandler
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

from autotrading.adapters.configuration.source import ConfigurationSource
from autotrading.adapters.outbound.grafana_cloud.composition import grafana_cloud_telemetry_adapters
from tests.support.http_recorder import recording_server

REPOSITORY = Path(__file__).resolve().parents[4]
TOKEN = "glc_secret-token"  # noqa: S105 - a made-up token of a fake stack
# A whole service in a process of its own: the providers of OpenTelemetry are global and can be set only once.
SERVICE = """
import logging
import sys

import fastapi
from fastapi.testclient import TestClient
from opentelemetry import _logs, metrics, trace

from autotrading.adapters.configuration.source import ConfigurationSource
from autotrading.adapters.outbound.grafana_cloud.composition import grafana_cloud_telemetry_adapters

endpoint, token_file = sys.argv[1:3]
logging.getLogger().setLevel(logging.INFO)
grafana_cloud_telemetry_adapters(
    ConfigurationSource({
        "APP_ENVIRONMENT": "dev",
        "APP_VERSION": "1.4.0",
        "GRAFANA_OTLP_ENDPOINT": endpoint,
        "GRAFANA_INSTANCE_ID": "1932769",
        "GRAFANA_OTLP_TOKEN_FILE": token_file,
    }),
    "autotrading-api",
)
api = fastapi.FastAPI()
api.get("/health")(lambda: {})
TestClient(api).get("/health")
logging.getLogger("autotrading.test").info("servizio avviato")
for provider in (trace.get_tracer_provider(), metrics.get_meter_provider(), _logs.get_logger_provider()):
    provider.shutdown()
"""


@pytest.mark.parametrize(
    "configuration",
    [{}, {"GRAFANA_OTLP_ENDPOINT": "https://otlp.example.test/otlp", "GRAFANA_INSTANCE_ID": "1932769"}],
    ids=["nothing", "no-token"],
)
def test_without_the_settings_nothing_is_installed_and_the_service_starts_as_today(
    caplog: pytest.LogCaptureFixture, configuration: dict[str, str]
) -> None:
    with caplog.at_level(logging.INFO, logger="autotrading.telemetry"):
        grafana_cloud_telemetry_adapters(ConfigurationSource(configuration), "autotrading-api")

    assert not FastAPIInstrumentor().is_instrumented_by_opentelemetry
    assert not HTTPXClientInstrumentor().is_instrumented_by_opentelemetry
    assert not SQLAlchemyInstrumentor().is_instrumented_by_opentelemetry
    assert not [handler for handler in logging.getLogger().handlers if isinstance(handler, LoggingHandler)]
    assert "telemetria Grafana Cloud non configurata" in caplog.text


def test_with_the_settings_the_service_exports_traces_metrics_and_logs_to_grafana_cloud(tmp_path: Path) -> None:
    token_file = tmp_path / "grafana_otlp_token"
    token_file.write_text(f"{TOKEN}\n", encoding="utf-8")
    script = tmp_path / "service.py"
    script.write_text(SERVICE, encoding="utf-8")

    with recording_server() as server:
        finished = subprocess.run(
            [sys.executable, str(script), f"{server.address}/otlp", str(token_file)],
            cwd=REPOSITORY,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )

    assert finished.returncode == 0, finished.stderr
    assert sorted(set(server.paths())) == ["/otlp/v1/logs", "/otlp/v1/metrics", "/otlp/v1/traces"]
    exported = b"".join(request.body for request in server.requests)
    assert b"autotrading-api" in exported
    assert b"servizio avviato" in exported
    assert b"/health" in exported
    assert TOKEN not in finished.stdout + finished.stderr
