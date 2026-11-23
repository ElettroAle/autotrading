from collections.abc import Callable

import pytest

from autotrading.application.flows.transient_retry import RETRY_PAUSES_SECONDS, TransientRetry
from autotrading.domain.errors import AutotradingError
from tests.fakes.cycles import FakePermanentError, FakeTransientError
from tests.fakes.pause import FakePauseAdapter


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


def test_two_more_calls_after_5_and_15_seconds() -> None:
    assert RETRY_PAUSES_SECONDS == (5.0, 15.0)


def test_a_call_that_goes_through_is_made_once_without_waiting() -> None:
    pause, failed = FakePauseAdapter(), Attempts()
    call = _Failing()

    assert TransientRetry(pause).run(call, _listener(failed)) == "letto"
    assert (call.calls, pause.pauses, failed) == (1, [], [])


def test_a_temporary_error_is_called_again_after_the_first_pause() -> None:
    pause, failed = FakePauseAdapter(), Attempts()
    error = FakeTransientError("exchange non raggiungibile")
    call = _Failing(error)

    assert TransientRetry(pause).run(call, _listener(failed)) == "letto"
    assert (call.calls, pause.pauses) == (2, [5.0])
    assert failed == [(1, error)]


def test_three_temporary_errors_give_the_last_one_after_both_pauses() -> None:
    pause, failed = FakePauseAdapter(), Attempts()
    errors = [FakeTransientError(f"timeout {attempt}") for attempt in (1, 2, 3)]
    call = _Failing(*errors)

    with pytest.raises(FakeTransientError) as raised:
        TransientRetry(pause).run(call, _listener(failed))

    assert raised.value is errors[2]
    assert (call.calls, pause.pauses) == (3, [5.0, 15.0])
    assert failed == [(1, errors[0]), (2, errors[1]), (3, errors[2])]


def test_a_permanent_error_comes_out_at_once() -> None:
    pause, failed = FakePauseAdapter(), Attempts()
    error = FakePermanentError("credenziali del conto non valide")
    call = _Failing(error)

    with pytest.raises(FakePermanentError) as raised:
        TransientRetry(pause).run(call, _listener(failed))

    assert raised.value is error
    assert (call.calls, pause.pauses) == (1, [])
    assert failed == [(1, error)]


def test_a_permanent_error_after_a_temporary_one_stops_the_attempts() -> None:
    pause, failed = FakePauseAdapter(), Attempts()
    temporary, permanent = FakeTransientError("timeout"), FakePermanentError("credito esaurito")
    call = _Failing(temporary, permanent, FakeTransientError("mai chiamato"))

    with pytest.raises(FakePermanentError):
        TransientRetry(pause).run(call, _listener(failed))

    assert (call.calls, pause.pauses) == (2, [5.0])
    assert failed == [(1, temporary), (2, permanent)]
