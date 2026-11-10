from dataclasses import dataclass

from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId


@dataclass(frozen=True, slots=True)
class Tenant:
    id: TenantId
    owner: UserId

    @classmethod
    def found_for(cls, owner: UserId) -> Tenant:
        return cls(TenantId.new(), owner)
