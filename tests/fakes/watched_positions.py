"""Fake of the positions the platform watches for the stop that follows the price, as the table holds them under row
level security (R5.5.1, ADR sorveglianza-del-prezzo-per-lo-stop-che-segue)."""

from collections.abc import Collection

from autotrading.application.tenancy.errors import CrossTenantAccessError
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.watched_position import WatchedPosition
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.flow_repository import FlowStore


class WatchedPositionStore:
    """The watched positions of every tenant, by flow and asset, and every save, as the database holds them."""

    def __init__(self) -> None:
        self.positions: dict[tuple[TenantId, FlowId, str], WatchedPosition] = {}
        self.saves = 0

    def of(self, tenant_id: TenantId, flow_id: FlowId) -> tuple[WatchedPosition, ...]:
        return tuple(
            position for (tenant, flow, _), position in self.positions.items() if (tenant, flow) == (tenant_id, flow_id)
        )


class InMemoryWatchedPositionsAdapter:
    """Bound to one tenant, like the real adapter: a flow of another tenant is refused."""

    def __init__(self, store: WatchedPositionStore, flows: FlowStore, tenant_id: TenantId) -> None:
        self._store = store
        self._flows = flows
        self._tenant_id = tenant_id

    def watched_of(self, flow_id: FlowId) -> tuple[WatchedPosition, ...]:
        return self._store.of(self._tenant_id, flow_id)

    def save(self, flow_id: FlowId, position: WatchedPosition) -> None:
        if not any(flow.id == flow_id for flow in self._flows.of(self._tenant_id)):
            raise CrossTenantAccessError
        self._store.positions[self._tenant_id, flow_id, position.asset] = position
        self._store.saves += 1

    def forget(self, flow_id: FlowId, asset: str) -> None:
        self._store.positions.pop((self._tenant_id, flow_id, asset), None)

    def keep_only(self, flow_ids: Collection[FlowId]) -> None:
        for key in [key for key in self._store.positions if key[0] == self._tenant_id and key[1] not in flow_ids]:
            del self._store.positions[key]
