from abc import ABC

from autotrading.domain.tenancy.tenant_id import TenantId


class TenantOwned(ABC):
    """Base of every entity that belongs to a tenant: it always says to whom it belongs (rule context-tenancy)."""

    __slots__ = ()
    tenant_id: TenantId
