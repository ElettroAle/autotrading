"""Fake of the levels of the protections in force of the flows: read from the protections the platform placed."""

from autotrading.domain.flows.exit_plan import PlacedLevels
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.orders.protection_kind import ProtectionKind
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.protection_repository import ProtectionStore


class InMemoryFlowProtectionLevelsAdapter:
    """Bound to one tenant, like the real adapter under row level security."""

    def __init__(self, store: ProtectionStore, tenant_id: TenantId) -> None:
        self._store = store
        self._tenant_id = tenant_id

    def placed_levels(self, flow_id: FlowId, asset: str) -> PlacedLevels:
        prices = {
            protection.kind: protection.trigger_price
            for tenant_id, protection in self._store.protections
            if tenant_id == self._tenant_id and (protection.flow_id, protection.asset) == (flow_id.value, asset)
        }
        return PlacedLevels(prices.get(ProtectionKind.STOP_LOSS), prices.get(ProtectionKind.TAKE_PROFIT))
