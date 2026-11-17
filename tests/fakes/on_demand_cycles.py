from collections.abc import Callable
from uuid import UUID

from autotrading.application.flows.errors import CycleWorkerUnavailableError
from autotrading.domain.errors import AutotradingError
from autotrading.domain.flows.cycle_record import CycleRecord


class FakeOnDemandCycleAdapter:
    """The worker reached in process instead of over HTTP: the cycle the worker runs now, for the same tenant."""

    def __init__(self, worker: Callable[[UUID], CycleRecord]) -> None:
        self._worker = worker
        self.reachable = True
        self.refusal: AutotradingError | None = None
        self.asked: list[UUID] = []

    def run(self, flow_id: UUID) -> CycleRecord:
        self.asked.append(flow_id)
        if not self.reachable:
            raise CycleWorkerUnavailableError
        if self.refusal is not None:
            raise self.refusal
        return self._worker(flow_id)
