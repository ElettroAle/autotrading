import logging
import threading

import pytest

from autotrading.adapters.outbound.threads.cycle_launcher import ThreadCycleLauncherAdapter
from autotrading.domain.errors import AutotradingError

WAITING = 5.0


class PermanentExampleError(AutotradingError):
    permanent = True

    def __init__(self) -> None:
        super().__init__("credito esaurito presso openrouter")


def test_the_cycle_runs_apart_from_the_caller() -> None:
    started, release, finished = threading.Event(), threading.Event(), threading.Event()

    def cycle() -> None:
        started.set()
        release.wait(WAITING)
        finished.set()

    ThreadCycleLauncherAdapter().launch(cycle)

    assert started.wait(WAITING)
    assert not finished.is_set()
    release.set()
    assert finished.wait(WAITING)


def test_an_error_out_of_the_cycle_is_logged_and_never_raised(caplog: pytest.LogCaptureFixture) -> None:
    done = threading.Event()

    def cycle() -> None:
        try:
            raise PermanentExampleError
        finally:
            done.set()

    with caplog.at_level(logging.WARNING, logger="autotrading.cycles"):
        ThreadCycleLauncherAdapter().launch(cycle)
        assert done.wait(WAITING)
        for thread in threading.enumerate():
            if thread.name == "cycle":
                thread.join(WAITING)

    [entry] = [record for record in caplog.records if record.name == "autotrading.cycles"]
    assert entry.getMessage() == "ciclo interrotto da un errore permanente"
    assert entry.__dict__["error"] == "credito esaurito presso openrouter"
