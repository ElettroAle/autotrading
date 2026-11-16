"""Fake of the recorder of the positions closed by their stop loss or take profit on the exchange (R3.1.2)."""

from autotrading.domain.flows.account_reconciliation import ProtectionClosing


class InMemoryProtectionClosingsAdapter:
    def __init__(self) -> None:
        self.closed: list[ProtectionClosing] = []

    def execute(self, closing: ProtectionClosing) -> None:
        self.closed.append(closing)
