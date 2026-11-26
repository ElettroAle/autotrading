"""What the schedulers of the checks of the worker share on APScheduler (ADR controllo-giornaliero-delle-scadenze, ADR
sorveglianza-del-prezzo-per-lo-stop-che-segue)."""

import logging
from datetime import timedelta, timezone

import pytest

from autotrading.adapters.outbound.apscheduler.check_scheduler import _check_background_scheduler, _run_check
from autotrading.domain.errors import AutotradingError

OPERATIONS = logging.getLogger("autotrading.tests.checks")
ROME_IN_WINTER = timezone(timedelta(hours=1))


class UnreachableExampleError(AutotradingError):
    def __init__(self) -> None:
        super().__init__("database non raggiungibile")


def _failing() -> None:
    raise UnreachableExampleError


def test_an_error_of_the_project_is_logged_with_the_logger_and_the_warning_given(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING, logger=OPERATIONS.name):
        _run_check("scadenze", _failing, OPERATIONS, "controllo di prova interrotto")

    [record] = caplog.records
    assert (record.name, record.getMessage()) == (OPERATIONS.name, "controllo di prova interrotto")
    assert record.__dict__["check"] == "scadenze"
    assert record.__dict__["error"] == "database non raggiungibile"


def test_a_check_that_succeeds_logs_nothing(caplog: pytest.LogCaptureFixture) -> None:
    runs: list[str] = []

    with caplog.at_level(logging.WARNING, logger=OPERATIONS.name):
        _run_check("scadenze", lambda: runs.append("scadenze"), OPERATIONS, "controllo di prova interrotto")

    assert runs == ["scadenze"]
    assert caplog.records == []


def test_the_scheduler_of_the_checks_waits_for_its_first_check_in_the_zone_given() -> None:
    scheduler = _check_background_scheduler(1, ROME_IN_WINTER)

    assert not scheduler.running
    assert scheduler.timezone == ROME_IN_WINTER
