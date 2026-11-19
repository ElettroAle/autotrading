from collections.abc import Callable

from autotrading.application.sources.errors import SourceUnansweredError


class FakeConcurrentCallsAdapter:
    """Runs the call at once in the thread of the test and remembers the wait it was given; when the test says the
    source stays silent the wait ends without an answer (R1.2.5)."""

    def __init__(self) -> None:
        self.silent = False
        self.waits: list[float] = []

    def call_within[R](self, call: Callable[[], R], seconds: float) -> R:
        self.waits.append(seconds)
        if self.silent:
            raise SourceUnansweredError(seconds)
        return call()
