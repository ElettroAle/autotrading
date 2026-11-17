from collections.abc import Sequence


class FakeEmergencyClosingNoticeAdapter:
    """Keeps the emergency closings a use case tells, instead of sending them to the chat of the tenant."""

    def __init__(self) -> None:
        self.told: list[tuple[int, tuple[str, ...]]] = []

    def execute(self, positions_closed: int, paused_flows: Sequence[str]) -> None:
        self.told.append((positions_closed, tuple(paused_flows)))
