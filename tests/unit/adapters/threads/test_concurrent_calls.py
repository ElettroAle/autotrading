"""Every call at once, awaited only up to a wait: what the sources of a cycle need (R1.2.5, ADR 0087)."""

import threading

import pytest

from autotrading.adapters.outbound.threads.concurrent_calls import ThreadPoolConcurrentCallsAdapter
from autotrading.application.cycles.ports import CallAnswered, CallFailed, CallUnanswered
from tests.fakes.cycles import FakeTransientError

WAIT_SECONDS = 1.0


def test_every_call_that_answers_in_time_gives_its_value() -> None:
    outcomes = ThreadPoolConcurrentCallsAdapter().call_all({"a": lambda: 1, "b": lambda: 2}, WAIT_SECONDS)

    assert outcomes == {"a": CallAnswered(1), "b": CallAnswered(2)}


def test_the_calls_run_together() -> None:
    both = threading.Barrier(2, timeout=WAIT_SECONDS)

    def meet() -> int:
        return both.wait()

    outcomes = ThreadPoolConcurrentCallsAdapter().call_all({"a": meet, "b": meet}, WAIT_SECONDS)

    assert all(isinstance(outcome, CallAnswered) for outcome in outcomes.values())


def test_a_call_still_running_is_abandoned_without_being_awaited() -> None:
    released = threading.Event()
    try:
        outcomes = ThreadPoolConcurrentCallsAdapter().call_all({"silent": released.wait}, 0.05)
    finally:
        released.set()

    assert outcomes == {"silent": CallUnanswered()}


def test_a_call_that_fails_with_a_project_error_gives_the_error() -> None:
    error = FakeTransientError("limite di richieste superato")

    def fail() -> int:
        raise error

    outcomes = ThreadPoolConcurrentCallsAdapter().call_all({"a": fail}, WAIT_SECONDS)

    assert outcomes == {"a": CallFailed(error)}


def test_a_defect_of_a_call_is_not_hidden() -> None:
    def broken() -> int:
        return 1 // 0

    with pytest.raises(ZeroDivisionError):
        ThreadPoolConcurrentCallsAdapter().call_all({"a": broken}, WAIT_SECONDS)
