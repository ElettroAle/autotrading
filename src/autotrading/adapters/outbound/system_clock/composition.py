from autotrading.adapters.outbound.system_clock.clock import SystemClockAdapter
from autotrading.adapters.outbound.system_clock.configuration import _SystemClockSettings
from autotrading.adapters.outbound.system_clock.pause import SystemClockPauseAdapter


def system_clock_adapters() -> SystemClockAdapter:
    """The clock of the machine, the only source of the current instant."""
    return SystemClockAdapter(_SystemClockSettings().zone)


def system_clock_pause_adapters() -> SystemClockPauseAdapter:
    """The pause of the machine, before the model is asked again in the same cycle."""
    return SystemClockPauseAdapter()
