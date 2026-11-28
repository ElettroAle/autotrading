from collections.abc import Callable

from autotrading.application.flows.ports import FlowTenantsPort
from autotrading.domain.tenancy.tenant_id import TenantId


def every_tenant(tenants: FlowTenantsPort, check_of: Callable[[TenantId], None]) -> Callable[[], None]:
    """A periodic check of the worker run for every tenant of the platform, each on the ports bound to it."""

    def check_every_tenant() -> None:
        for tenant_id in tenants.tenant_ids():
            check_of(tenant_id)

    return check_every_tenant
