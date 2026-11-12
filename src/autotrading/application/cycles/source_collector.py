from collections.abc import Callable, Sequence
from concurrent.futures import Future, ThreadPoolExecutor
from concurrent.futures import wait as wait_for
from datetime import timedelta
from uuid import UUID

from autotrading.application.cycles.ports import SourcePort, SourceReading
from autotrading.domain.cycles.cycle_record import AbsentSource
from autotrading.domain.errors import AutotradingError

type Outcomes = tuple[list[SourceReading], list[AbsentSource]]


def real_seconds(wait: timedelta) -> float:
    return wait.total_seconds()


class SourceCollector:
    """Asks every active source at once and waits for them only up to the wait of the cycle (R1.2.5)."""

    def __init__(self, sources: SourcePort, seconds_of: Callable[[timedelta], float] = real_seconds) -> None:
        self._sources = sources
        # The tests compress time; the cycle waits for real seconds.
        self._seconds_of = seconds_of

    def collect(self, flow_id: UUID, sources: Sequence[str], wait: timedelta) -> Outcomes:
        if not sources:
            return [], []
        executor = ThreadPoolExecutor(max_workers=len(sources), thread_name_prefix="source")
        futures = {source: executor.submit(self._sources.collect, flow_id, source) for source in sources}
        answered, _ = wait_for(futures.values(), timeout=self._seconds_of(wait))
        # A source still running is abandoned, never awaited: the cycle goes on without it.
        executor.shutdown(wait=False, cancel_futures=True)
        outcomes = [_outcome_of(source, future, future in answered, wait) for source, future in futures.items()]
        readings = [outcome for outcome in outcomes if isinstance(outcome, SourceReading)]
        absent = [outcome for outcome in outcomes if isinstance(outcome, AbsentSource)]
        return readings, absent


def _outcome_of(source: str, future: Future[object], answered: bool, wait: timedelta) -> SourceReading | AbsentSource:
    if not answered:
        return AbsentSource(source, f"nessuna risposta entro {int(wait.total_seconds())} secondi")
    error = future.exception()
    if error is None:
        return SourceReading(source, future.result())
    if not isinstance(error, AutotradingError):
        raise error
    return AbsentSource(source, str(error))
