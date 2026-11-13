"""The records of the application reach the output of the container, with their moment (ADR 0102)."""

import io
import json
import logging
import logging.config
from collections.abc import Iterator
from pathlib import Path

import pytest

from autotrading.adapters.inbound.api.logging_setup import UtcFormatter

ROOT = Path(__file__).resolve().parents[4]
LOGGING_CONFIGURATION = ROOT / "deploy" / "logging.json"
NAMED_LOGGERS = ("uvicorn", "uvicorn.error", "uvicorn.access", "httpx", "httpcore", "autotrading.credentials")


@pytest.fixture
def configured(monkeypatch: pytest.MonkeyPatch) -> Iterator[io.StringIO]:
    root = logging.getLogger()
    saved_root = (list(root.handlers), root.level)
    saved = {name: (logging.getLogger(name).level, list(logging.getLogger(name).handlers)) for name in NAMED_LOGGERS}
    output = io.StringIO()
    monkeypatch.setattr("sys.stdout", output)
    logging.config.dictConfig(json.loads(LOGGING_CONFIGURATION.read_text(encoding="utf-8")))
    yield output
    root.handlers[:], level = saved_root
    root.setLevel(level)
    for name, (logger_level, handlers) in saved.items():
        logging.getLogger(name).setLevel(logger_level)
        logging.getLogger(name).handlers[:] = handlers


def test_an_info_record_of_the_application_reaches_the_output_with_its_utc_moment(configured: io.StringIO) -> None:
    logging.getLogger("autotrading.credentials").info("decifratura riuscita per %s", "ordini")

    moment, rest = configured.getvalue().strip().split(" ", 1)
    assert rest == "INFO autotrading.credentials decifratura riuscita per ordini"
    assert moment.endswith("Z")
    assert "T" in moment


def test_the_requests_of_the_http_clients_stay_out_of_the_output(configured: io.StringIO) -> None:
    logging.getLogger("httpx").info("HTTP Request: POST https://api.telegram.org/bot<token>/sendMessage")

    assert configured.getvalue() == ""


def test_the_moment_is_written_in_utc() -> None:
    record = logging.LogRecord("autotrading", logging.INFO, __file__, 1, "x", None, None)
    record.created = 0.0

    assert UtcFormatter("%(asctime)s", "%Y-%m-%dT%H:%M:%SZ").format(record) == "1970-01-01T00:00:00Z"


@pytest.mark.parametrize("service", ["create_application", "create_worker_application"])
def test_both_services_start_with_the_logging_configuration(service: str) -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    compose = (ROOT / "deploy" / "compose.yaml").read_text(encoding="utf-8")
    start = next(line for line in (dockerfile + compose).splitlines() if f"bootstrap:{service}" in line)

    assert '"--log-config", "/app/logging.json"' in start
    assert "COPY deploy/logging.json /app/logging.json" in dockerfile
