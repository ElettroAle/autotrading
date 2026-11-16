"""Fake of the record of the emergency closings: those of every tenant, bound to one per request."""

from autotrading.application.tenancy.errors import CrossTenantAccessError
from autotrading.domain.flows.emergency_closing import EmergencyClosing
from autotrading.domain.tenancy.tenant_id import TenantId


class InMemoryEmergencyClosingLogAdapter:
    """Bound to one tenant, like the real adapter under row level security."""

    def __init__(self, store: list[EmergencyClosing], tenant_id: TenantId) -> None:
        self._store = store
        self._tenant_id = tenant_id

    def record(self, closing: EmergencyClosing) -> None:
        if closing.tenant_id != self._tenant_id:
            raise CrossTenantAccessError
        self._store.append(closing)
