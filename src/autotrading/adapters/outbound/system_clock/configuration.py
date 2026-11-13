from dataclasses import dataclass
from datetime import UTC, tzinfo


@dataclass(frozen=True, slots=True)
class _SystemClockSettings:
    """Every instant of the platform is in UTC: the cycles, the records and the exchange agree on it."""

    zone: tzinfo = UTC
