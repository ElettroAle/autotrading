from autotrading.application.notifications.ports import NotifiedFlow
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.flow_repository import FlowStore


class InMemoryNotifiedFlowsAdapter:
    """The flows of one tenant not archived, from the store of the flows, as the SQLAlchemy adapter reads them."""

    def __init__(self, store: FlowStore, tenant_id: TenantId) -> None:
        self._store = store
        self._tenant_id = tenant_id

    def list(self) -> tuple[NotifiedFlow, ...]:
        flows = [flow for flow in self._store.of(self._tenant_id) if flow.status is not FlowStatus.ARCHIVED]
        return tuple(
            NotifiedFlow(flow.id.value, flow.name.value) for flow in sorted(flows, key=lambda each: each.name.value)
        )
