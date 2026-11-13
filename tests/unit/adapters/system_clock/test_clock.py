"""The clock of the machine, always in UTC: the platform stores and compares instants in UTC."""

from datetime import UTC, datetime

from autotrading.adapters.outbound.system_clock.clock import SystemClockAdapter
from autotrading.adapters.outbound.system_clock.composition import system_clock_adapters
from autotrading.adapters.outbound.system_clock.configuration import _SystemClockSettings


def test_the_clock_reads_the_instant_of_the_machine_in_utc() -> None:
    before = datetime.now(UTC)

    read = SystemClockAdapter().now()

    assert before <= read <= datetime.now(UTC)
    assert read.tzinfo is UTC


def test_the_composition_builds_the_clock_of_the_settings() -> None:
    assert isinstance(system_clock_adapters(), SystemClockAdapter)
    assert _SystemClockSettings().zone is UTC
