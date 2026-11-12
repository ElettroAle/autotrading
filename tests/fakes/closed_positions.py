"""Fake of the history of the closed positions of the flows."""

from autotrading.domain.flows.account_reconciliation import OutsideClosing


class InMemoryClosedPositionsAdapter:
    def __init__(self) -> None:
        self.closed: list[OutsideClosing] = []

    def add_closed_outside(self, closing: OutsideClosing) -> None:
        self.closed.append(closing)
