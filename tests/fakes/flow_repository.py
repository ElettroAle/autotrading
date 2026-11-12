"""Fake of the repository of the flows: the database of every tenant, bound to one per request."""

from autotrading.application.flows.errors import FlowNameInUseError
from autotrading.application.tenancy.errors import CrossTenantAccessError
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_name import FlowName
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.tenancy.tenant_id import TenantId


class FlowStore:
    """The flows of every tenant, as the database holds them."""

    def __init__(self) -> None:
        self.flows: list[Flow] = []

    def of(self, tenant_id: TenantId) -> list[Flow]:
        return [flow for flow in self.flows if flow.tenant_id == tenant_id]


class InMemoryFlowRepositoryAdapter:
    """Bound to one tenant, like the real adapter under row level security."""

    def __init__(self, store: FlowStore, tenant_id: TenantId) -> None:
        self._store = store
        self._tenant_id = tenant_id

    def list(self) -> list[Flow]:
        return self._store.of(self._tenant_id)

    def name_in_use(self, name: FlowName) -> bool:
        return any(flow.name == name and flow.status != FlowStatus.ARCHIVED for flow in self.list())

    def add(self, flow: Flow) -> None:
        if flow.tenant_id != self._tenant_id:
            raise CrossTenantAccessError
        if self.name_in_use(flow.name):
            raise FlowNameInUseError
        self._store.flows.append(flow)
