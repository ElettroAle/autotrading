from collections.abc import Callable
from uuid import UUID

from autotrading.application.flows.ports import CycleFailureNoticePort, FlowTenantPort
from autotrading.domain.tenancy.tenant_id import TenantId


class TellCycleFailureUseCase:
    """Tells a failed cycle to the tenant of its flow, and to nobody else (R1.8.2, R0.1.3)."""

    def __init__(self, tenants: FlowTenantPort, notices_of: Callable[[TenantId], CycleFailureNoticePort]) -> None:
        self._tenants = tenants
        self._notices_of = notices_of

    def execute(self, flow_id: UUID, reason: str) -> None:
        self._notices_of(self._tenants.tenant_of(flow_id)).execute(flow_id, reason)
