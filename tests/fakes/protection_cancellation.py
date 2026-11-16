"""Fake of the cancellation of the protections a closing leaves on the exchange (R3.1.2)."""

from autotrading.application.flows.ports import ProtectedPosition


class FakeProtectionCancellationAdapter:
    def __init__(self) -> None:
        self.cancelled: list[ProtectedPosition] = []

    def execute(self, position: ProtectedPosition) -> None:
        self.cancelled.append(position)
