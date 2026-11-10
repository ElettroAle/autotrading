from dataclasses import dataclass

from autotrading.application.tenancy.errors import TenantAlreadyExistsError
from autotrading.application.tenancy.ports import TenantRepositoryPort
from autotrading.domain.tenancy.tenant import Tenant
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId


@dataclass(frozen=True, slots=True)
class ResolveTenantCommand:
    user_id: UserId


class ResolveTenantUseCase:
    """Finds the tenant of a user, founding it at the first access (R0.1.2)."""

    def __init__(self, tenants: TenantRepositoryPort) -> None:
        self._tenants = tenants

    def execute(self, command: ResolveTenantCommand) -> TenantId:
        existing = self._tenants.find_by_member(command.user_id)
        if existing is not None:
            return existing.id
        return self._found_tenant_for(command.user_id)

    def _found_tenant_for(self, user_id: UserId) -> TenantId:
        tenant = Tenant.found_for(user_id)
        try:
            self._tenants.add(tenant)
        except TenantAlreadyExistsError:
            # Two first requests of the same user raced: the one that lost keeps the tenant the other founded.
            return self._existing_tenant_of(user_id)
        return tenant.id

    def _existing_tenant_of(self, user_id: UserId) -> TenantId:
        existing = self._tenants.find_by_member(user_id)
        if existing is None:
            raise TenantAlreadyExistsError(user_id)
        return existing.id
