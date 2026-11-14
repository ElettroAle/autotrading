"""Fake of the repository of the closed positions: the positions of every tenant, bound to one per request."""

from autotrading.application.tenancy.errors import CrossTenantAccessError
from autotrading.domain.flows.closed_position import ClosedPosition
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.statistics_period import TimeWindow
from autotrading.domain.tenancy.tenant_id import TenantId


class ClosedPositionStore:
    def __init__(self) -> None:
        self.positions: list[ClosedPosition] = []


class InMemoryClosedPositionRepositoryAdapter:
    """Bound to one tenant, like the real adapter under row level security; newest first, like the real adapter."""

    def __init__(self, store: ClosedPositionStore, tenant_id: TenantId) -> None:
        self._store = store
        self._tenant_id = tenant_id

    def add(self, position: ClosedPosition) -> None:
        if position.tenant_id != self._tenant_id:
            raise CrossTenantAccessError
        self._store.positions.append(position)

    def newest(self, flow_id: FlowId, offset: int, limit: int) -> list[ClosedPosition]:
        of_flow = sorted(
            self._of_flow(flow_id),
            key=lambda position: position.closing.at,
            reverse=True,
        )
        return of_flow[offset : offset + limit]

    def closed_within(self, flow_id: FlowId, window: TimeWindow) -> list[ClosedPosition]:
        return [position for position in self._of_flow(flow_id) if window.contains(position.closing.at)]

    def _of_flow(self, flow_id: FlowId) -> list[ClosedPosition]:
        return [
            position
            for position in self._store.positions
            if position.tenant_id == self._tenant_id and position.flow_id == flow_id
        ]
