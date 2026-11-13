from datetime import UTC, datetime, tzinfo


class SystemClockAdapter:
    """The instant of the machine, in the zone the platform stores and compares instants in."""

    def __init__(self, zone: tzinfo = UTC) -> None:
        self._zone = zone

    def now(self) -> datetime:
        return datetime.now(self._zone)
