"""Fake of the suspension of the openings of the flows: what the store keeps beside each flow (R3.2.2)."""

from dataclasses import replace
from datetime import datetime
from uuid import UUID

from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.openings_suspension import NOT_SUSPENDED, OpeningsStatus, OpeningsSuspension
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.flow_repository import FlowStore


class InMemoryOpeningsSuspensionAdapter:
    """Bound to one tenant, like the real adapter under row level security: a flow of another tenant is never touched
    and reads as never suspended.
    """

    def __init__(self, store: FlowStore, tenant_id: TenantId) -> None:
        self._store = store
        self._tenant_id = tenant_id

    def status(self, flow_id: UUID) -> OpeningsStatus:
        if not self._owns(flow_id):
            return NOT_SUSPENDED
        return self._store.openings.get(FlowId(flow_id), NOT_SUSPENDED)

    def suspend(self, flow_id: UUID, suspension: OpeningsSuspension) -> None:
        if self._owns(flow_id):
            self._store.openings[FlowId(flow_id)] = replace(self.status(flow_id), suspension=suspension)

    def resume(self, flow_id: UUID, resumed_at: datetime) -> None:
        if self._owns(flow_id):
            self._store.openings[FlowId(flow_id)] = OpeningsStatus(None, resumed_at)

    def _owns(self, flow_id: UUID) -> bool:
        return any(flow.id.value == flow_id for flow in self._store.of(self._tenant_id))
