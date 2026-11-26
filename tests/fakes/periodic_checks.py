"""Fake of the scheduler of the periodic checks of the worker (R5.5.1, ADR
sorveglianza-del-prezzo-per-lo-stop-che-segue)."""

from collections.abc import Callable
from datetime import timedelta


class FakePeriodicCheckSchedulerAdapter:
    """Keeps the periodic checks it is given; a test runs them as the scheduler would, at once and at every interval."""

    def __init__(self) -> None:
        self.checks: dict[str, tuple[timedelta, Callable[[], None]]] = {}

    def keep_every(self, name: str, every: timedelta, run: Callable[[], None]) -> None:
        self.checks[name] = (every, run)

    def run_all(self) -> None:
        for _, run in self.checks.values():
            run()
