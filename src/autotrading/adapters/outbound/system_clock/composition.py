from autotrading.adapters.outbound.system_clock.clock import SystemClockAdapter
from autotrading.adapters.outbound.system_clock.configuration import _SystemClockSettings


def system_clock_adapters() -> SystemClockAdapter:
    """The clock of the machine, the only source of the current instant."""
    return SystemClockAdapter(_SystemClockSettings().zone)
