from collections.abc import Callable
from datetime import timedelta

from autotrading.application.cycles.ports import (
    CallAnswered,
    CallFailed,
    CallOutcome,
    ConcurrentCallsPort,
    SourcePort,
    SourceReading,
    SourceRequest,
)
from autotrading.domain.cycles.cycle_record import AbsentSource

type Outcomes[D] = tuple[list[SourceReading[D]], list[AbsentSource]]


def real_seconds(wait: timedelta) -> float:
    return wait.total_seconds()


class SourceCollector[S = object, D = object]:
    """Asks every active source at once and waits for them only up to the wait of the cycle (R1.2.5)."""

    def __init__(
        self,
        sources: SourcePort[S, D],
        calls: ConcurrentCallsPort,
        seconds_of: Callable[[timedelta], float] = real_seconds,
    ) -> None:
        self._sources = sources
        self._calls = calls
        # The tests compress time; the cycle waits for real seconds.
        self._seconds_of = seconds_of

    def collect(self, request: SourceRequest[S], wait: timedelta) -> Outcomes[D]:
        calls = {source: self._asking(request, source) for source in request.snapshot.sources}
        outcomes = self._calls.call_all(calls, self._seconds_of(wait))
        results = [_result_of(source, outcome, wait) for source, outcome in outcomes.items()]
        readings = [result for result in results if not isinstance(result, AbsentSource)]
        absent = [result for result in results if isinstance(result, AbsentSource)]
        return readings, absent

    def _asking(self, request: SourceRequest[S], source: str) -> Callable[[], D]:
        return lambda: self._sources.collect(request, source)


def _result_of[D](source: str, outcome: CallOutcome[D], wait: timedelta) -> SourceReading[D] | AbsentSource:
    if isinstance(outcome, CallAnswered):
        return SourceReading(source, outcome.value)
    if isinstance(outcome, CallFailed):
        return AbsentSource(source, str(outcome.error))
    return AbsentSource(source, f"nessuna risposta entro {int(wait.total_seconds())} secondi")
