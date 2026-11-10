from typing import Protocol

from autotrading.domain.tenancy.tenant import Tenant
from autotrading.domain.tenancy.user_id import UserId


class TenantRepositoryPort(Protocol):
    def find_by_member(self, user_id: UserId) -> Tenant | None: ...

    def add(self, tenant: Tenant) -> None:
        """Raises TenantAlreadyExistsError when the owner is already a member of a tenant."""
        ...
