"""Fake of the repository of the flows: the database of every tenant, bound to one per request."""

from collections.abc import Sequence
from dataclasses import replace

from autotrading.application.flows.errors import FlowNameInUseError, FlowNotFoundError, FlowVersionNotFoundError
from autotrading.application.tenancy.errors import CrossTenantAccessError
from autotrading.domain.flows.capital_change import CapitalChange
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_configuration import FlowConfiguration
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.flow_name import FlowName
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.tenancy.tenant_id import TenantId


class FlowStore:
    """The flows of every tenant with the version in force, and every version, as the database holds them."""

    def __init__(self) -> None:
        self.flows: list[Flow] = []
        self.pause_reasons: dict[FlowId, str] = {}
        self.versions: dict[FlowId, list[FlowConfiguration]] = {}
        self.capital_changes: dict[FlowId, list[CapitalChange]] = {}

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
        self._store.versions[flow.id] = [flow.configuration]

    def get(self, flow_id: FlowId) -> Flow:
        flow = next((flow for flow in self.list() if flow.id == flow_id), None)
        if flow is None:
            raise FlowNotFoundError
        return flow

    def version(self, flow_id: FlowId, number: int) -> FlowConfiguration:
        self.get(flow_id)
        configuration = next((each for each in self._store.versions[flow_id] if each.version == number), None)
        if configuration is None:
            raise FlowVersionNotFoundError(number)
        return configuration

    def change_status(self, flow: Flow) -> None:
        self._replace(replace(self.get(flow.id), status=flow.status))

    def add_version(self, flow: Flow) -> None:
        self._replace(replace(self.get(flow.id), configuration=flow.configuration))
        self._store.versions[flow.id].append(flow.configuration)

    def add_capital_change(self, flow: Flow, change: CapitalChange) -> None:
        self.add_version(flow)
        self._store.capital_changes.setdefault(flow.id, []).append(change)

    def capital_changes(self, flow_id: FlowId) -> tuple[CapitalChange, ...]:
        self.get(flow_id)
        return tuple(self._store.capital_changes.get(flow_id, []))

    def _replace(self, flow: Flow) -> None:
        self._store.flows = [flow if each.id == flow.id else each for each in self._store.flows]


class InMemoryAutomaticPauseAdapter:
    """Bound to one tenant: pauses only its active flows, keeping the reason beside them."""

    def __init__(self, store: FlowStore, tenant_id: TenantId) -> None:
        self._store = store
        self._tenant_id = tenant_id

    def pause(self, flow_ids: Sequence[FlowId], reason: str) -> None:
        for index, flow in enumerate(self._store.flows):
            if flow.tenant_id == self._tenant_id and flow.id in flow_ids and flow.status is FlowStatus.ACTIVE:
                self._store.flows[index] = replace(flow, status=FlowStatus.PAUSED)
                self._store.pause_reasons[flow.id] = reason
