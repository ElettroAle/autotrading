from collections.abc import Callable, Mapping
from concurrent.futures import Future, ThreadPoolExecutor
from concurrent.futures import wait as wait_for

from autotrading.application.flows.ports import CallAnswered, CallFailed, CallOutcome, CallUnanswered
from autotrading.domain.errors import AutotradingError


class ThreadPoolConcurrentCallsAdapter:
    """Runs the calls in threads of a pool of their own, one each, and waits only up to the seconds (R1.2.5)."""

    def call_all[R](self, calls: Mapping[str, Callable[[], R]], seconds: float) -> dict[str, CallOutcome[R]]:
        if not calls:
            return {}
        executor = ThreadPoolExecutor(max_workers=len(calls), thread_name_prefix="call")
        futures = {name: executor.submit(call) for name, call in calls.items()}
        answered, _ = wait_for(futures.values(), timeout=seconds)
        # A call still running is abandoned, never awaited: the caller goes on without it.
        executor.shutdown(wait=False, cancel_futures=True)
        return {name: _outcome_of(future, future in answered) for name, future in futures.items()}


def _outcome_of[R](future: Future[R], answered: bool) -> CallOutcome[R]:
    if not answered:
        return CallUnanswered()
    error = future.exception()
    if error is None:
        return CallAnswered(future.result())
    if not isinstance(error, AutotradingError):
        raise error
    return CallFailed(error)
