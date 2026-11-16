from dataclasses import dataclass

from autotrading.domain.notifications.email_address import EmailAddress
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.tenant_owned import TenantOwned


@dataclass(frozen=True, slots=True)
class NotificationEmail(TenantOwned):
    """The only address a tenant's notifications go to by email (R3.5.2)."""

    tenant_id: TenantId
    address: EmailAddress
