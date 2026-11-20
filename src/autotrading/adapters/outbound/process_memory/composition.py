from collections.abc import Callable

from autotrading.adapters.outbound.process_memory.account_activity import (
    ProcessMemoryAccountActivityAdapter,
    _AccountActivityStore,
)
from autotrading.adapters.outbound.process_memory.configuration import _ProcessMemorySettings
from autotrading.application.flows.ports import AccountActivityPort
from autotrading.domain.tenancy.tenant_id import TenantId

type RememberedAccountActivity = Callable[[AccountActivityPort, TenantId], ProcessMemoryAccountActivityAdapter]


def process_memory_adapters() -> RememberedAccountActivity:
    """One store for the process; for each request, the reading of the account decorated with it for its tenant."""
    store = _AccountActivityStore(_ProcessMemorySettings().account_activity_validity_seconds)

    def remembered(activity: AccountActivityPort, tenant_id: TenantId) -> ProcessMemoryAccountActivityAdapter:
        return ProcessMemoryAccountActivityAdapter(activity, tenant_id, store)

    return remembered
