"""The retry of the cycle for the tests of the contexts that use it outside a cycle."""

from datetime import UTC, datetime

from autotrading.application.flows.transient_retry import TransientRetry
from tests.fakes.cycles import FakeClockAdapter
from tests.fakes.pause import FakePauseAdapter


def unlimited_retry(waits: FakePauseAdapter) -> TransientRetry:
    """No cycle sets its limit: every attempt starts, after the pauses the waits record."""
    return TransientRetry(waits, FakeClockAdapter(datetime(2026, 11, 23, 8, 50, tzinfo=UTC)))
