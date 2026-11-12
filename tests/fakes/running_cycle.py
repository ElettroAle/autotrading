"""Fake of the cycles the worker runs, as the flows context waits for them: waiting lets the cycle end first."""

from collections.abc import Callable

from autotrading.domain.flows.flow_id import FlowId


class FakeRunningCycleAdapter:
    def __init__(self, orders_sent: Callable[[], int]) -> None:
        self._orders_sent = orders_sent
        self.running: set[FlowId] = set()
        # Each cycle that ended while someone waited, with the orders the exchange had received by then.
        self.ended: list[tuple[FlowId, int]] = []

    def wait_until_finished(self, flow_id: FlowId) -> None:
        if flow_id not in self.running:
            return
        self.running.remove(flow_id)
        self.ended.append((flow_id, self._orders_sent()))
