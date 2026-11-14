"""Fake of the repository of the equity of the cycles: the equity of every tenant, bound to one per request."""

from datetime import datetime
from uuid import UUID

from autotrading.domain.flows.equity_period import EquityWindow
from autotrading.domain.flows.equity_snapshot import EquitySnapshot
from autotrading.domain.tenancy.tenant_id import TenantId


class EquitySnapshotStore:
    def __init__(self) -> None:
        self.snapshots: dict[tuple[TenantId, UUID, datetime], EquitySnapshot] = {}


class InMemoryEquitySnapshotRepositoryAdapter:
    """Bound to one tenant, like the real adapter under row level security; a cycle keeps its first equity."""

    def __init__(self, store: EquitySnapshotStore, tenant_id: TenantId) -> None:
        self._store = store
        self._tenant_id = tenant_id

    def record(self, snapshot: EquitySnapshot) -> None:
        self._store.snapshots.setdefault((self._tenant_id, snapshot.flow_id, snapshot.planned_at), snapshot)

    def of_flow(self, flow_id: UUID, window: EquityWindow) -> list[EquitySnapshot]:
        return sorted(
            (
                snapshot
                for (tenant_id, owner, _), snapshot in self._store.snapshots.items()
                if tenant_id == self._tenant_id and owner == flow_id and window.admits(snapshot.planned_at)
            ),
            key=lambda snapshot: snapshot.planned_at,
        )
