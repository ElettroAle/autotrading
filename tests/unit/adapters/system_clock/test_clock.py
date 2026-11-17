"""The clock of the machine, always in UTC: the platform stores and compares instants in UTC; and its pause."""

import time
from datetime import UTC, datetime

from autotrading.adapters.outbound.system_clock.clock import SystemClockAdapter
from autotrading.adapters.outbound.system_clock.composition import system_clock_adapters, system_clock_pause_adapters
from autotrading.adapters.outbound.system_clock.configuration import _SystemClockSettings
from autotrading.adapters.outbound.system_clock.pause import SystemClockPauseAdapter


def test_the_clock_reads_the_instant_of_the_machine_in_utc() -> None:
    before = datetime.now(UTC)

    read = SystemClockAdapter().now()

    assert before <= read <= datetime.now(UTC)
    assert read.tzinfo is UTC


def test_the_composition_builds_the_clock_of_the_settings() -> None:
    assert isinstance(system_clock_adapters(), SystemClockAdapter)
    assert _SystemClockSettings().zone is UTC


def test_the_pause_waits_at_least_the_seconds_asked_for() -> None:
    before = time.monotonic()

    SystemClockPauseAdapter().pause(0.05)

    assert time.monotonic() - before >= 0.05


def test_the_composition_builds_the_pause_of_the_machine() -> None:
    assert isinstance(system_clock_pause_adapters(), SystemClockPauseAdapter)
