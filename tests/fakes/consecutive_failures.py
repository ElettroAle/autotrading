"""Fake of the count of the failed cycles in a row: the recorded cycles and the anchor the store keeps (R3.2.4)."""

from uuid import UUID

from autotrading.domain.flows.cycle_record import CycleOutcome
from autotrading.domain.flows.flow_id import FlowId
from tests.fakes.cycles import InMemoryCycleRepositoryAdapter
from tests.fakes.flow_repository import FlowStore


class InMemoryConsecutiveFailuresAdapter:
    """Counts as the real adapter does: after the last completed cycle and since the flow last became active."""

    def __init__(self, cycles: InMemoryCycleRepositoryAdapter, store: FlowStore) -> None:
        self._cycles = cycles
        self._store = store

    def consecutive_failures(self, flow_id: UUID) -> int:
        anchor = self._store.anchors.get(FlowId(flow_id))
        since_anchor = sorted(
            (
                record
                for record in self._cycles.records
                if record.flow_id == flow_id and (anchor is None or record.planned_at >= anchor)
            ),
            key=lambda record: record.planned_at,
        )
        failures = 0
        for record in since_anchor:
            if record.outcome is CycleOutcome.COMPLETED:
                failures = 0
            if record.outcome is CycleOutcome.FAILED:
                failures += 1
        return failures
