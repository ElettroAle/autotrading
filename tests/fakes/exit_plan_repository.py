"""Fake of the repository of the exit plans in force: the plans of every tenant, bound to one per request."""

from autotrading.domain.flows.exit_plan import ExitPlan
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.tenancy.tenant_id import TenantId


class ExitPlanStore:
    def __init__(self) -> None:
        self.plans: dict[tuple[TenantId, FlowId, str], ExitPlan] = {}


class InMemoryExitPlanRepositoryAdapter:
    """Bound to one tenant, like the real adapter under row level security: one plan per flow and asset."""

    def __init__(self, store: ExitPlanStore, tenant_id: TenantId) -> None:
        self._store = store
        self._tenant_id = tenant_id

    def current(self, flow_id: FlowId, asset: str) -> ExitPlan | None:
        return self._store.plans.get((self._tenant_id, flow_id, asset))

    def save(self, flow_id: FlowId, asset: str, plan: ExitPlan) -> None:
        self._store.plans[self._tenant_id, flow_id, asset] = plan

    def remove(self, flow_id: FlowId, asset: str) -> None:
        self._store.plans.pop((self._tenant_id, flow_id, asset), None)
