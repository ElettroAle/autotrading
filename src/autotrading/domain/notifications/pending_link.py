from dataclasses import dataclass
from datetime import datetime, timedelta

from autotrading.domain.notifications.link_code import LinkCode
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.tenant_owned import TenantOwned

VALIDITY = timedelta(minutes=15)


@dataclass(frozen=True, slots=True)
class PendingLink(TenantOwned):
    """A link code a tenant asked for: valid 15 minutes and only once (R1.8.1)."""

    tenant_id: TenantId
    digest: bytes
    issued_at: datetime
    used: bool = False

    @classmethod
    def issue(cls, tenant_id: TenantId, code: LinkCode, now: datetime) -> PendingLink:
        return cls(tenant_id, code.digest, now)

    @property
    def expires_at(self) -> datetime:
        return self.issued_at + VALIDITY

    def usable_at(self, now: datetime) -> bool:
        return not self.used and now <= self.expires_at
