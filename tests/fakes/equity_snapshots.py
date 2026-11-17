"""Fake of the repository of the equity of the cycles: the equity of every tenant, bound to one per request."""

from datetime import datetime
from uuid import UUID

from autotrading.domain.flows.equity_snapshot import EquitySnapshot
from autotrading.domain.flows.loss_guard import LossReferences
from autotrading.domain.flows.statistics_period import TimeWindow
from autotrading.domain.tenancy.tenant_id import TenantId


class EquitySnapshotStore:
    def __init__(self) -> None:
        self.snapshots: dict[tuple[TenantId, UUID, datetime], EquitySnapshot] = {}


class InMemoryEquitySnapshotRepositoryAdapter:
    """Bound to one tenant, like the real adapter under row level security; a cycle keeps its first equity.

    It gives the references of the losses as the real adapter does (R3.2.2).
    """

    def __init__(self, store: EquitySnapshotStore, tenant_id: TenantId) -> None:
        self._store = store
        self._tenant_id = tenant_id

    def record(self, snapshot: EquitySnapshot) -> None:
        self._store.snapshots.setdefault((self._tenant_id, snapshot.flow_id, snapshot.planned_at), snapshot)

    def of_flow(self, flow_id: UUID, window: TimeWindow) -> list[EquitySnapshot]:
        return sorted(
            (
                snapshot
                for (tenant_id, owner, _), snapshot in self._store.snapshots.items()
                if tenant_id == self._tenant_id and owner == flow_id and window.contains(snapshot.planned_at)
            ),
            key=lambda snapshot: snapshot.planned_at,
        )

    def loss_references(self, flow_id: UUID, day_start: datetime, peak_since: datetime) -> LossReferences:
        recorded = self.of_flow(flow_id, TimeWindow(None, None))
        until_midnight = [snapshot for snapshot in recorded if snapshot.planned_at <= day_start]
        of_the_day = [snapshot for snapshot in recorded if snapshot.planned_at >= day_start]
        daily = until_midnight[-1] if until_midnight else next(iter(of_the_day), None)
        since = [snapshot for snapshot in recorded if snapshot.planned_at >= peak_since]
        peak = max(reversed(since), key=lambda snapshot: snapshot.equity - snapshot.allocated_capital, default=None)
        return LossReferences(daily, peak)
