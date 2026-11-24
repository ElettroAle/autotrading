from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest

from autotrading.application.flows.transient_retry import RETRY_PAUSES_SECONDS, TransientRetry
from autotrading.domain.errors import AutotradingError
from tests.fakes.cycles import FakeClockAdapter, FakePermanentError, FakeTransientError
from tests.fakes.pause import FakePauseAdapter

PLANNED_AT = datetime(2026, 11, 23, 8, 50, tzinfo=UTC)


class _Failing:
    """Fails with the errors it is given, one per call, then answers."""

    def __init__(self, *errors: AutotradingError) -> None:
        self._errors = list(errors)
        self.calls = 0

    def __call__(self) -> str:
        self.calls += 1
        if self._errors:
            raise self._errors.pop(0)
        return "letto"


class Attempts(list[tuple[int, AutotradingError]]):
    """The failed attempts the retry told, with their number."""


def _listener(failed: Attempts) -> Callable[[int, AutotradingError], None]:
    return lambda attempt, error: failed.append((attempt, error))


def _retry(pause: FakePauseAdapter) -> TransientRetry:
    return TransientRetry(pause, FakeClockAdapter(PLANNED_AT))


def _timed() -> tuple[FakePauseAdapter, TransientRetry]:
    """A retry whose pauses move its clock on, as the seconds it waits pass."""
    clock = FakeClockAdapter(PLANNED_AT)
    pause = FakePauseAdapter(clock=clock)
    return pause, TransientRetry(pause, clock)


def _always_failing() -> _Failing:
    return _Failing(*(FakeTransientError(f"timeout {attempt}") for attempt in range(1, 7)))


def test_five_more_calls_after_5_15_30_60_and_120_seconds() -> None:
    assert RETRY_PAUSES_SECONDS == (5.0, 15.0, 30.0, 60.0, 120.0)


def test_a_call_that_goes_through_is_made_once_without_waiting() -> None:
    pause, failed = FakePauseAdapter(), Attempts()
    call = _Failing()

    assert _retry(pause).run(call, _listener(failed)) == "letto"
    assert (call.calls, pause.pauses, failed) == (1, [], [])


def test_a_temporary_error_is_called_again_after_the_first_pause() -> None:
    pause, failed = FakePauseAdapter(), Attempts()
    error = FakeTransientError("exchange non raggiungibile")
    call = _Failing(error)

    assert _retry(pause).run(call, _listener(failed)) == "letto"
    assert (call.calls, pause.pauses) == (2, [5.0])
    assert failed == [(1, error)]


def test_six_temporary_errors_give_the_last_one_after_every_pause() -> None:
    pause, failed = FakePauseAdapter(), Attempts()
    errors = [FakeTransientError(f"timeout {attempt}") for attempt in range(1, 7)]
    call = _Failing(*errors)

    with pytest.raises(FakeTransientError) as raised:
        _retry(pause).run(call, _listener(failed))

    assert raised.value is errors[5]
    assert (call.calls, pause.pauses) == (6, [5.0, 15.0, 30.0, 60.0, 120.0])
    assert failed == [(attempt, error) for attempt, error in enumerate(errors, start=1)]


# ADR-ritentativo-del-ciclo-entro-meta-dell-intervallo: a new attempt starts only within the limit of the cycle.
def test_a_short_limit_stops_the_attempts_whose_wait_would_end_beyond_it() -> None:
    pause, retry = _timed()
    retry.limit_to(PLANNED_AT + timedelta(seconds=60))
    failed = Attempts()
    call = _always_failing()

    with pytest.raises(FakeTransientError, match="timeout 4"):
        retry.run(call, _listener(failed))

    assert (call.calls, pause.pauses) == (4, [5.0, 15.0, 30.0])
    assert [attempt for attempt, _ in failed] == [1, 2, 3, 4]


def test_a_long_limit_lets_every_attempt_start() -> None:
    pause, retry = _timed()
    retry.limit_to(PLANNED_AT + timedelta(minutes=7, seconds=30))
    call = _always_failing()

    with pytest.raises(FakeTransientError, match="timeout 6"):
        retry.run(call, _listener(Attempts()))

    assert (call.calls, pause.pauses) == (6, [5.0, 15.0, 30.0, 60.0, 120.0])


def test_an_attempt_whose_wait_ends_right_at_the_limit_still_starts() -> None:
    pause, retry = _timed()
    retry.limit_to(PLANNED_AT + timedelta(seconds=5))
    call = _always_failing()

    with pytest.raises(FakeTransientError, match="timeout 2"):
        retry.run(call, _listener(Attempts()))

    assert pause.pauses == [5.0]


def test_a_limit_already_past_leaves_the_first_attempt_only() -> None:
    pause, retry = _timed()
    retry.limit_to(PLANNED_AT - timedelta(seconds=1))
    call = _always_failing()

    with pytest.raises(FakeTransientError, match="timeout 1"):
        retry.run(call, _listener(Attempts()))

    assert (call.calls, pause.pauses) == (1, [])


def test_the_limit_counts_the_time_the_attempts_take() -> None:
    clock = FakeClockAdapter(PLANNED_AT, timedelta(seconds=10))
    pause = FakePauseAdapter(clock=clock)
    retry = TransientRetry(pause, clock)
    retry.limit_to(PLANNED_AT + timedelta(seconds=30))
    call = _always_failing()

    with pytest.raises(FakeTransientError):
        retry.run(call, _listener(Attempts()))

    # The attempts take 10 seconds each: checked at 0, waits 5; at 15, waits 15; at 40 a wait of 30 ends beyond 30.
    assert pause.pauses == [5.0, 15.0]


def test_a_permanent_error_comes_out_at_once() -> None:
    pause, failed = FakePauseAdapter(), Attempts()
    error = FakePermanentError("credenziali del conto non valide")
    call = _Failing(error)

    with pytest.raises(FakePermanentError) as raised:
        _retry(pause).run(call, _listener(failed))

    assert raised.value is error
    assert (call.calls, pause.pauses) == (1, [])
    assert failed == [(1, error)]


def test_a_permanent_error_after_a_temporary_one_stops_the_attempts() -> None:
    pause, failed = FakePauseAdapter(), Attempts()
    temporary, permanent = FakeTransientError("timeout"), FakePermanentError("credito esaurito")
    call = _Failing(temporary, permanent, FakeTransientError("mai chiamato"))

    with pytest.raises(FakePermanentError):
        _retry(pause).run(call, _listener(failed))

    assert (call.calls, pause.pauses) == (2, [5.0])
    assert failed == [(1, temporary), (2, permanent)]
